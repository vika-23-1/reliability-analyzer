#!/usr/bin/env python3
"""Пример использования reliability_engine."""

from reliability_engine import (
    Component, SeriesBlock, ParallelBlock, KofNBlock, CCFBlock,
    calculate_metrics
)


def main():
    # Создаём компоненты
    # Параметры: имя, MTBF (часы до отказа), MTTR (часы восстановления)
    disk = Component("Диск", mtbf=100000, mttr=2)
    db = Component("БД", mtbf=50000, mttr=1)
    cache = Component("Кеш", mtbf=30000, mttr=0.5)
    
    # Пример 1: Последовательное соединение
    print("=" * 60)
    print("Пример 1: Последовательная система (все элементы важны)")
    print("=" * 60)
    series = SeriesBlock([disk, db, cache], name="Основная система")
    metrics = calculate_metrics(series)
    for key, val in metrics.items():
        print(f"{key}: {val:.6f}" if isinstance(val, float) else f"{key}: {val}")
    
    # Пример 2: Параллельное резервирование
    print("\n" + "=" * 60)
    print("Пример 2: Параллельная система (резервирование)")
    print("=" * 60)
    disk1 = Component("Диск-1", mtbf=100000, mttr=2)
    disk2 = Component("Диск-2", mtbf=100000, mttr=2)
    parallel = ParallelBlock([disk1, disk2], name="Зеркалированные диски")
    metrics = calculate_metrics(parallel)
    for key, val in metrics.items():
        print(f"{key}: {val:.6f}" if isinstance(val, float) else f"{key}: {val}")
    
    # Пример 3: Кворум k-из-n (как в etcd/Raft)
    print("\n" + "=" * 60)
    print("Пример 3: Кворум 3-из-5 (etcd/Raft кластер)")
    print("=" * 60)
    nodes = [Component(f"Node-{i}", mtbf=50000, mttr=1) for i in range(1, 6)]
    quorum = KofNBlock(k=3, items=nodes, name="etcd кластер 3-из-5")
    metrics = calculate_metrics(quorum)
    for key, val in metrics.items():
        print(f"{key}: {val:.6f}" if isinstance(val, float) else f"{key}: {val}")
    
    # Пример 4: Система с общими причинами отказа
    print("\n" + "=" * 60)
    print("Пример 4: Система с CCF (например, общее питание)")
    print("=" * 60)
    srv1 = Component("Сервер-1", mtbf=80000, mttr=2)
    srv2 = Component("Сервер-2", mtbf=80000, mttr=2)
    ccf_system = CCFBlock([srv1, srv2], beta=0.1, name="Серверы с общим питанием")
    metrics = calculate_metrics(ccf_system)
    for key, val in metrics.items():
        print(f"{key}: {val:.6f}" if isinstance(val, float) else f"{key}: {val}")
    
    # Пример 5: Сложная система (комбинация)
    print("\n" + "=" * 60)
    print("Пример 5: Сложная архитектура")
    print("=" * 60)
    # БД слой: 2 основные БД в параллель + 1 резервная
    db1 = Component("БД-Primary-1", mtbf=60000, mttr=1)
    db2 = Component("БД-Primary-2", mtbf=60000, mttr=1)
    db_backup = Component("БД-Backup", mtbf=40000, mttr=2)
    db_layer = ParallelBlock([db1, db2, db_backup], name="БД слой с резервой")
    
    # Кеш слой: кворум 2-из-3
    cache_nodes = [Component(f"Cache-{i}", mtbf=30000, mttr=0.5) for i in range(1, 4)]
    cache_layer = KofNBlock(k=2, items=cache_nodes, name="Кеш слой 2-из-3")
    
    # Объединяем слои в серию (оба должны работать)
    complex_system = SeriesBlock([db_layer, cache_layer], name="Сложная система")
    metrics = calculate_metrics(complex_system)
    for key, val in metrics.items():
        print(f"{key}: {val:.6f}" if isinstance(val, float) else f"{key}: {val}")
    
    print("\n" + "=" * 60)
    print("Интерпретация результатов:")
    print("=" * 60)
    print("R(t) - вероятность безотказной работы за период")
    print("Availability - коэффициент готовности (доля времени, когда система работает)")
    print("Годовой простой - ожидаемое время простоя в году")


if __name__ == "__main__":
    main()
