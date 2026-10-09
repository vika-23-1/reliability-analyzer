import math
import numpy as np
import pandas as pd


class Component:
    """Одиночный элемент системы."""
    def __init__(self, name: str, mtbf: float, mttr: float):
        self.name = name
        self.mtbf = mtbf
        self.mttr = mttr
        self.lmbda = 1.0 / mtbf if mtbf > 0 else 0.0

    def reliability(self, t: float) -> float:
        """Вероятность безотказной работы R(t) = e^(-lambda * t)"""
        return math.exp(-self.lmbda * t)

    def availability(self) -> float:
        """Коэффициент готовности A = MTBF / (MTBF + MTTR)"""
        return self.mtbf / (self.mtbf + self.mttr) if (self.mtbf + self.mttr) > 0 else 0.0


class SeriesBlock:
    """Последовательное соединение (все элементы должны быть исправны)."""
    def __init__(self, items: list, name: str = "Последовательный блок"):
        self.items = items
        self.name = name

    def reliability(self, t: float) -> float:
        """R_sys = R1 * R2 * ... * Rn"""
        r = 1.0
        for item in self.items:
            r *= item.reliability(t)
        return r

    def availability(self) -> float:
        """A_sys = A1 * A2 * ... * An"""
        a = 1.0
        for item in self.items:
            a *= item.availability()
        return a


class ParallelBlock:
    """Параллельное резервирование 1-из-N."""
    def __init__(self, items: list, name: str = "Параллельный блок"):
        self.items = items
        self.name = name

    def reliability(self, t: float) -> float:
        """R_sys = 1 - (1 - R1) * (1 - R2) * ... * (1 - Rn)"""
        unreliability = 1.0
        for item in self.items:
            unreliability *= (1.0 - item.reliability(t))
        return 1.0 - unreliability

    def availability(self) -> float:
        """A_sys = 1 - (1 - A1) * (1 - A2) * ... * (1 - An)"""
        unavail = 1.0
        for item in self.items:
            unavail *= (1.0 - item.availability())
        return 1.0 - unavail


class KofNBlock:
    """Блок кворума k-из-n (например, etcd / Raft).
    
    Система работает, если минимум k из n компонентов исправны.
    Используется биномиальное распределение для расчёта надёжности.
    """
    def __init__(self, k: int, items: list, name: str = "k-из-n Блок"):
        self.k = k
        self.items = items
        self.n = len(items)
        self.name = name

    def reliability(self, t: float) -> float:
        """R_sys = Sum(i=k to n) C(n,i) * R^i * (1-R)^(n-i)"""
        # Для идентичных компонентов используем биномиальное распределение
        r_single = self.items[0].reliability(t)
        r_total = 0.0
        for i in range(self.k, self.n + 1):
            comb = math.comb(self.n, i)
            r_total += comb * (r_single ** i) * ((1.0 - r_single) ** (self.n - i))
        return r_total

    def availability(self) -> float:
        """A_sys = Sum(i=k to n) C(n,i) * A^i * (1-A)^(n-i)"""
        a_single = self.items[0].availability()
        a_total = 0.0
        for i in range(self.k, self.n + 1):
            comb = math.comb(self.n, i)
            a_total += comb * (a_single ** i) * ((1.0 - a_single) ** (self.n - i))
        return a_total


class CCFBlock:
    """Параллельный блок с учётом общих причин отказа (Beta-Factor Model).
    
    Интенсивность отказов разделяется на:
    - Независимые отказы: (1-β)λ
    - Общие причины отказа: βλ (например, общее питание, стойка, коммутатор)
    
    Формула: R_sys = R_parallel * e^(-beta*lambda*t)
    """
    def __init__(self, items: list, beta: float, name: str = "Блок с CCF"):
        self.items = items
        self.beta = beta  # Доля отказов по общей причине (0.0 - 1.0)
        self.name = name
        self.n = len(items)

    def reliability(self, t: float) -> float:
        """R_sys = (1 - (1-R_ind)^n) * e^(-beta*lambda*t)"""
        lmbda = self.items[0].lmbda
        lmbda_ind = (1.0 - self.beta) * lmbda
        lmbda_ccf = self.beta * lmbda

        # Надёжность одного компонента с независимой интенсивностью отказов
        r_ind_single = math.exp(-lmbda_ind * t)
        
        # Вероятность работы хотя бы одного элемента из n (параллельная система)
        r_ind_parallel = 1.0 - ((1.0 - r_ind_single) ** self.n)
        
        # Вероятность того, что общая причина отказа не произойдёт
        r_ccf = math.exp(-lmbda_ccf * t)

        return r_ind_parallel * r_ccf

    def availability(self) -> float:
        """A_sys = (1 - (1-A_ind)^n) * A_ccf (приближённо)"""
        a_single = self.items[0].availability()
        
        # Приближенная модель: разделяем неготовность по независимой и общей причине
        unavail_ind = 1.0 - a_single
        
        # Готовность независимого параллельного резерва
        a_ind_parallel = 1.0 - (unavail_ind ** self.n)
        
        # Приближённая готовность системы с CCF
        # Предполагаем, что CCF добавляет независимую неготовность
        unavail_ccf = (1.0 - a_single) * self.beta
        
        return a_ind_parallel * (1.0 - unavail_ccf)


def calculate_metrics(system, t_period: float = 720.0, hours_per_year: float = 8760.0) -> dict:
    """Рассчитывает ключевые SRE-метрики для системы.
    
    Args:
        system: Объект системы (Component, SeriesBlock, ParallelBlock, KofNBlock или CCFBlock)
        t_period: Расчётный период (часы), по умолчанию 1 месяц (720 ч)
        hours_per_year: Часов в году (обычно 8760)
    
    Returns:
        dict: Словарь с метриками R(t), A, простоем в часах и секундах
    """
    r_val = system.reliability(t_period)
    a_val = system.availability()
    downtime_hours = (1.0 - a_val) * hours_per_year
    downtime_sec = downtime_hours * 3600

    return {
        "Система": system.name,
        "R(t)": r_val,
        "Availability": a_val,
        "Годовой простой (ч)": downtime_hours,
        "Годовой простой (сек)": downtime_sec
    }
