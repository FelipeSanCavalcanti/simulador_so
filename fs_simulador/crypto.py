"""Criptografia simulada de dados em repouso.

O simulador não usa bibliotecas externas: o texto claro é combinado (XOR)
com um fluxo determinístico derivado de SHA-256(chave + salt + bloco).
Assim, o conteúdo gravado no bloco físico é sempre ciphertext e só pode ser
lido de volta com a mesma chave.
"""

import hashlib
import secrets


def new_salt():
    return secrets.token_hex(8)


def _keystream(key, salt, block_index, length):
    """Fluxo de bytes determinístico para um bloco específico."""
    seed = f"{key}|{salt}|{block_index}".encode("utf-8")
    stream = b""
    counter = 0

    while len(stream) < length:
        stream += hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        counter += 1

    return stream[:length]


def _xor(data, key, salt, block_index):
    stream = _keystream(key, salt, block_index, len(data))
    return bytes(a ^ b for a, b in zip(data, stream))


def encrypt_chunk(text, key, salt, block_index):
    """Criptografa um trecho de texto e devolve o ciphertext em hexadecimal."""
    return _xor(text.encode("utf-8"), key, salt, block_index).hex()


def decrypt_chunk(cipher_hex, key, salt, block_index):
    """Reverte encrypt_chunk. Retorna '' para blocos ainda sem conteúdo."""
    if not cipher_hex:
        return ""

    try:
        data = bytes.fromhex(cipher_hex)
    except ValueError:
        return ""

    return _xor(data, key, salt, block_index).decode("utf-8", errors="replace")


def fingerprint(text):
    """SHA-256 do texto claro, usado para validar a chave no acesso."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
