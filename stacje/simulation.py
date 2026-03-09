import numpy as np
from dataclasses import dataclass, field


@dataclass
class ChannelState:
    remaining_time: float = 0.0
    call_duration: float = 0.0
    served_count: int = 0
    is_busy: bool = False


@dataclass
class QueueItem:
    call_duration: float = 0.0
    wait_time: float = 0.0


@dataclass
class StepResult:
    channels: list = field(default_factory=list)
    queue: list = field(default_factory=list)
    queue_len: int = 0
    rho: float = 0.0
    avg_q: float = 0.0
    avg_w: float = 0.0
    current_time: int = 0
    total_served: int = 0
    rejected: int = 0
    new_calls: int = 0
    finished: bool = False


class SimulationEngine:
    def __init__(self, num_channels, queue_size, lam, n_mean, sigma, min_dur, max_dur, sim_time):
        self.num_channels = num_channels
        self.queue_size = queue_size
        self.lam = lam
        self.n_mean = n_mean
        self.sigma = sigma
        self.min_dur = min_dur
        self.max_dur = max_dur
        self.sim_time = sim_time

        self.channels = [ChannelState() for _ in range(num_channels)]
        self.queue = []
        self.current_time = 0
        self.total_served = 0
        self.rejected = 0

        self.rho_history = []
        self.q_history = []
        self.w_history = []
        self.time_history = []

        self._total_wait = 0.0
        self._total_calls_queued = 0

        # generujemy całą listę przybyć z góry
        self.arrivals = []
        self._generate_arrivals()
        self._arrival_index = 0
        self._arrival_accumulator = 0.0

    def _generate_arrivals(self):
        # generujemy czasy między przybyciami z rozkładu wykładniczego
        # (proces Poissona z parametrem lambda <=> czasy między zdarzeniami Exp(1/lambda))
        total = 0.0
        lambdas = []
        while total <= self.sim_time:
            inter = np.random.exponential(1.0 / self.lam) if self.lam > 0 else float('inf')
            lambdas.append(inter)
            total += inter

        # dla każdego przybycia losujemy czas rozmowy z rozkładu Gaussa,
        # obcinamy do [Min, Maks]
        for lam_i in lambdas:
            mu_i = np.random.normal(self.n_mean, self.sigma)
            mu_i = float(np.clip(mu_i, self.min_dur, self.max_dur))
            mu_i = round(mu_i)
            self.arrivals.append((lam_i, mu_i))

    def step(self) -> StepResult:
        if self.current_time >= self.sim_time:
            return StepResult(finished=True, current_time=self.current_time)

        self.current_time += 1

        # tick - odejmujemy 1s od aktywnych połączeń
        for ch in self.channels:
            if ch.is_busy:
                ch.remaining_time -= 1
                if ch.remaining_time <= 0:
                    ch.is_busy = False
                    ch.remaining_time = 0
                    ch.call_duration = 0
                    self.total_served += 1
                    ch.served_count += 1

        # z kolejki przenosimy do właśnie zwolnionych kanałów
        while self.queue:
            free_ch = self._find_free_channel()
            if free_ch is None:
                break
            item = self.queue.pop(0)
            self._total_wait += item.wait_time
            self._total_calls_queued += 1
            free_ch.is_busy = True
            free_ch.remaining_time = item.call_duration
            free_ch.call_duration = item.call_duration

        # pobierz k elementów z listy λ takich że:
        #   suma(λ_1..λ_{k-1}) < 1  oraz  suma(λ_1..λ_k) >= 1
        # czyli zbieramy kolejne inter-arrival times aż ich suma dobije do 1 sekundy,
        # każde zdarzenie PRZED przekroczeniem progu = połączenie przychodzące w tej sekundzie
        new_calls = self._get_new_calls()

        # umieszczamy nowe połączenia w kanałach lub kolejce
        for _, mu_i in new_calls:
            free_ch = self._find_free_channel()
            if free_ch is not None:
                free_ch.is_busy = True
                free_ch.remaining_time = mu_i
                free_ch.call_duration = mu_i
            elif len(self.queue) < self.queue_size:
                self.queue.append(QueueItem(call_duration=mu_i, wait_time=0))
            else:
                self.rejected += 1

        # każde połączenie w kolejce czeka kolejną sekundę
        for item in self.queue:
            item.wait_time += 1

        # liczymy metryki
        busy = sum(1 for ch in self.channels if ch.is_busy)
        rho = busy / self.num_channels if self.num_channels > 0 else 0.0
        # Q = bieżąca długość kolejki
        q = float(len(self.queue))
        # W = skumulowana średnia czasu oczekiwania połączeń które wyszły z kolejki
        w = (self._total_wait / self._total_calls_queued) if self._total_calls_queued > 0 else 0.0

        self.rho_history.append(rho)
        self.q_history.append(q)
        self.w_history.append(w)
        self.time_history.append(self.current_time)

        return StepResult(
            channels=[(ch.is_busy, ch.remaining_time, ch.call_duration, ch.served_count) for ch in self.channels],
            queue=[(item.call_duration, item.wait_time) for item in self.queue],
            queue_len=len(self.queue),
            rho=rho,
            avg_q=q,
            avg_w=w,
            current_time=self.current_time,
            total_served=self.total_served,
            rejected=self.rejected,
            new_calls=len(new_calls),
            finished=self.current_time >= self.sim_time
        )

    def _get_new_calls(self):
     
        #bierzemy k elementów z listy λ takich że:
        #suma(λ_i, i=1..k-1) < 1  oraz  suma(λ_i, i=1..k) >= 1

        #Akumulator jest trwały między krokami - reszta po przekroczeniu
        #1 sekundy przenosi się na następny krok.
    
        calls = []
        while self._arrival_index < len(self.arrivals):
            lam_i, mu_i = self.arrivals[self._arrival_index]
            self._arrival_accumulator += lam_i
            self._arrival_index += 1
            calls.append((lam_i, mu_i))
            if self._arrival_accumulator >= 1.0:
                # przekroczyliśmy 1s - reszta przechodzi na następną sekundę
                self._arrival_accumulator -= 1.0
                break
        return calls

    def _find_free_channel(self):
        for ch in self.channels:
            if not ch.is_busy:
                return ch
        return None

    def get_results_for_file(self):
        lines = [
            "=== Parametry symulacji ===",
            f"Liczba kanalów: {self.num_channels}",
            f"Dlugosc kolejki: {self.queue_size}",
            f"Lambda: {self.lam}",
            f"N (srednia dlugosci rozmowy): {self.n_mean}",
            f"Sigma: {self.sigma}",
            f"Min: {self.min_dur}",
            f"Maks: {self.max_dur}",
            f"Czas symulacji: {self.sim_time}",
            "",
            "=== Wyniki ===",
            f"{'Czas':<10}{'Rho':<15}{'Q':<15}{'W':<15}",
            "-" * 55,
        ]
        for i in range(len(self.time_history)):
            lines.append(
                f"{self.time_history[i]:<10}{self.rho_history[i]:<15.6f}"
                f"{self.q_history[i]:<15.6f}{self.w_history[i]:<15.6f}"
            )
        return "\n".join(lines) + "\n"
