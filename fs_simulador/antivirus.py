"""Módulo de integridade e antivírus simulado.

A varredura faz duas checagens por arquivo:
1) Integridade: o hash SHA-256 de cada bloco físico é comparado ao registro
   oficial mantido pelo SecurityManager (gravado em toda escrita legítima).
   Uma escrita direta no bloco (bypass) diverge do registro e gera ALERTA.
2) Assinaturas maliciosas: o texto claro é comparado a uma lista de padrões.
Arquivos criptografados são validados por hash e reportados como íntegros,
sem expor o conteúdo.
"""

import hashlib

MALICIOUS_SIGNATURES = (
    "eicar-test-signature",
    "x5o!p%@ap[4\\pzx54(p^)7cc)7}",
    "malware",
    "backdoor",
    "rootkit",
    "keylogger",
    "rm -rf /",
)

INTEGRITY_NOTE = (
    "Possível modificação direta não autorizada no bloco do disco."
)


class AntivirusScanner:
    """Executa a auditoria do sistema de arquivos."""

    def __init__(self, filesystem, security):
        self.fs = filesystem
        self.security = security

    def scan(self, path="/"):
        self.security.require_session()

        target = self.fs.resolve(path)
        files = self._collect(target)

        print("\n[MÓDULO DE SEGURANÇA - VARREDURA DE INTEGRIDADE]")
        print(
            f"Analisando {len(files)} arquivos em busca de assinaturas "
            "maliciosas e hashes corrompidos..."
        )

        if not files:
            print("Nenhum arquivo encontrado no caminho informado.")
            return

        threats = 0
        alerts = 0

        for node in files:
            file_path = self.fs.get_path(node)
            integrity, signatures, encrypted = self._inspect(node)

            alerts += len(integrity)
            threats += len(signatures)

            if integrity:
                print(
                    f"- {file_path:<32}: [ALERTA] {integrity[0]}"
                )
                for issue in integrity[1:]:
                    print(f"  - [ALERTA] {issue}")
                for issue in signatures:
                    print(f"  - [AMEACA] {issue}")
                print(f"  Resultado: {INTEGRITY_NOTE}")
            elif signatures:
                print(f"- {file_path:<32}: [AMEACA] {signatures[0]}")
                for issue in signatures[1:]:
                    print(f"  - [AMEACA] {issue}")
                print("  Resultado: conteúdo com assinatura maliciosa detectada.")
            elif encrypted:
                print(f"- {file_path:<32}: [OK - Criptografado e Íntegro]")
            elif node.size == 0:
                print(f"- {file_path:<32}: [OK - Sem conteúdo gravado]")
            else:
                print(f"- {file_path:<32}: [OK - Íntegro]")

        print(
            f"\nArquivos analisados: {len(files)} | "
            f"Ameaças: {threats} | Alertas de integridade: {alerts}"
        )

        if threats or alerts:
            print("Resultado: anomalias detectadas. Verifique os logs de auditoria.")
        else:
            print("Resultado: nenhuma anomalia detectada. Sistema íntegro.")

        self.security.log(
            f"ANTIVIRUS: varredura de '{path}' - {len(files)} arquivos, "
            f"{threats} ameaças, {alerts} alertas de integridade"
        )

    # ---------- Auxiliares ----------
    def _collect(self, target):
        if target.is_file():
            return [target]

        return self.fs._list_files(target)

    def _inspect(self, node):
        """Retorna (alertas_de_integridade, assinaturas, criptografado)."""
        integrity = []

        for index in node.data_blocks:
            block = self.fs.disk.blocks[index]

            if block is None:
                integrity.append(f"Bloco {index:02d} registrado no i-node está livre!")
                continue

            content = block.get("content") or ""
            official = self.security.integrity_registry.get(index)

            if official is None:
                continue

            recomputed = hashlib.sha256(content.encode("utf-8")).hexdigest()

            if recomputed != official:
                integrity.append(
                    f"Hash do bloco {index:02d} difere do registro oficial!"
                )

        if node.encrypted:
            return integrity, [], True

        text = self.fs.plaintext(node).lower()
        signatures = [
            f"Assinatura maliciosa detectada: '{signature}'"
            for signature in MALICIOUS_SIGNATURES
            if signature in text
        ]

        return integrity, signatures, False
