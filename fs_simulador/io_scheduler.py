class DiskScheduler:
    """Simula o escalonamento das requisições de E/S do disco."""

    def __init__(self, total_tracks=16, head_position=0):
        self.total_tracks = total_tracks
        self.head_position = head_position

    def validate_requests(self, requests):
        for track in requests:
            if not isinstance(track, int) or not 0 <= track < self.total_tracks:
                raise ValueError(f"Trilha inválida: {track}")

    def calculate_movement(self, path):
        return sum(
            abs(path[i] - path[i - 1])
            for i in range(1, len(path))
        )

    def fcfs(self, requests):
        """Atende na ordem de chegada."""
        return list(requests)

    def sstf(self, requests):
        """Atende primeiro a requisição mais próxima."""
        pending = list(requests)
        current = self.head_position
        order = []

        while pending:
            nearest = min(
                pending,
                key=lambda track: abs(track - current)
            )

            order.append(nearest)
            pending.remove(nearest)
            current = nearest

        return order

    def scan(self, requests, direction="right"):
        """Move até a extremidade e depois inverte a direção."""
        if not requests:
            return []
        
        if direction == "right":
            right = sorted(t for t in requests if t >= self.head_position)
            left = sorted(
                (t for t in requests if t < self.head_position),
                reverse=True
            )
            return right + [self.total_tracks - 1] + left

        left = sorted(
            (t for t in requests if t <= self.head_position),
            reverse=True
        )
        right = sorted(t for t in requests if t > self.head_position)
        return left + [0] + right

    def cscan(self, requests, direction="right"):
        """Atende em uma direção e retorna ao início sem atender na volta."""
        if not requests:
            return []
        
        if direction == "right":
            right = sorted(t for t in requests if t >= self.head_position)
            left = sorted(t for t in requests if t < self.head_position)

            return right + [self.total_tracks - 1, 0] + left

        left = sorted(
            (t for t in requests if t <= self.head_position),
            reverse=True
        )
        right = sorted(
            (t for t in requests if t > self.head_position),
            reverse=True
        )

        return left + [0, self.total_tracks - 1] + right

    def schedule(self, requests, algorithm="SSTF", direction="right"):
        self.validate_requests(requests)

        #movement = self.calculate_movement(path)
        
        #self.head_position = path[-1]

        algorithms = {
            "FCFS": self.fcfs,
            "SSTF": self.sstf,
            "SCAN": lambda r: self.scan(r, direction),
            "C-SCAN": lambda r: self.cscan(r, direction)
        }

        algorithm = algorithm.upper()

        if algorithm not in algorithms:
            raise ValueError("Algoritmo não reconhecido.")

        path = [self.head_position] + algorithms[algorithm](requests)

        movement = self.calculate_movement(path)

        print("\n========== ESCALONAMENTO DE DISCO ==========")
        print(f"Algoritmo: {algorithm}")
        print(f"Posição inicial: {self.head_position}")
        print(f"Ordem de movimentação: {' -> '.join(map(str, path))}")
        print(f"Deslocamento total: {movement} blocos")
        print("============================================")

        return {
            "algorithm": algorithm,
            "path": path,
            "movement": movement
        }
