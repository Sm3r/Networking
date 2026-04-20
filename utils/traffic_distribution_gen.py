#!/usr/bin/env python3
import argparse, numpy as np
from pathlib import Path

def timeToSeconds(time, uom):
    seconds = time
    if uom == "H": seconds *= 60
    if uom in ["H", "m"]: seconds *= 60
    return seconds


def getSplineValue(t, points):
    if len(points) < 2: return 0
    p1_idx = next((i for i, p in enumerate(points) if p['x'] >= t), -1)
    if p1_idx == -1: return points[-1]['y']
    if p1_idx == 0: return points[0]['y']
    p0_idx = max(0, p1_idx - 2)
    p2_idx = p1_idx
    p1_idx_adj = p1_idx - 1
    p3_idx = min(len(points) - 1, p1_idx + 1)
    p0, p1, p2, p3 = points[p0_idx], points[p1_idx_adj], points[p2_idx], points[p3_idx]
    nt = (t - p1['x']) / (p2['x'] - p1['x']) if (p2['x'] - p1['x'] != 0) else 0
    if np.isnan(nt) or not np.isfinite(nt): nt = 0
    t2 = nt * nt
    t3 = t2 * nt
    a = 0.5 * (2 * p1['y'])
    b = 0.5 * (p2['y'] - p0['y'])
    c = 0.5 * (2 * p0['y'] - 5 * p1['y'] + 4 * p2['y'] - p3['y'])
    d = 0.5 * (-p0['y'] + 3 * p1['y'] - 3 * p2['y'] + p3['y'])
    return a + (b * nt) + (c * t2) + (d * t3)


def generateRandomPoints(pointCount, yMin, yMax, duration):
    pointCount = max(2, pointCount)
    controlPoints = [None] * pointCount
    yRescale = lambda v, s, off: v * s + off
    offset = yMin
    scale = yMax - yMin
    period = duration
    dt = 1 / (pointCount - 1)
    y = yRescale(0.3, scale, offset)
    controlPoints[0] = {'x': 0, 'y': y}
    controlPoints[pointCount - 1] = {'x': period, 'y': y}
    yMaxRange = dt * 6
    for i in range(1, pointCount - 1):
        x = i * dt * period
        y = yRescale((np.random.random() * 2 - 1) * yMaxRange, scale, y)
        y = min(max(y, yMin), yMax)
        controlPoints[i] = {'x': x, 'y': y}
    return controlPoints


def exportToCSV(duration, interval, controlPoints, yMin, yMax):
    sampledData = []
    totalValue = 0
    ts = 0
    while ts <= duration:
        value = getSplineValue(ts, controlPoints)
        value = max(yMin, min(yMax, value))
        value = max(0, value)
        sampledData.append({'timestamp': ts, 'value': value})
        totalValue += value
        ts += interval
    csvContent = "UnixTimestamp,NormalizedPacketCount\n"
    for data in sampledData:
        normalizedValue = 0 if totalValue == 0 else (data['value'] / totalValue)
        csvContent += f"{int(data['timestamp'])},{normalizedValue}\n"
    return csvContent

def generate_traffic_signal(duration=30, unit='m', y_min=0, y_max=100, interval=1, interval_unit='s', points=61, output=None, seed=None, verbose=True):
    """
    Generate traffic signal CSV data using Catmull-Rom spline interpolation.
    
    Args:
        duration: Duration value
        unit: Time unit ('s', 'm', 'H')
        y_min: Minimum packet count
        y_max: Maximum packet count
        interval: Sampling interval
        interval_unit: Interval unit ('s', 'm', 'H')
        points: Number of random control points
        output: Output file path (None = return as string)
        seed: Random seed for reproducibility
        verbose: Print progress messages
    
    Returns:
        CSV content as string if output=None, else writes to file and returns filepath
    """
    if seed is not None:
        np.random.seed(seed)
    
    dur = timeToSeconds(duration, unit)
    ival = timeToSeconds(interval, interval_unit)
    
    if verbose:
        print(f"Generating: {duration}{unit} = {dur}s, {points} points")
    
    pts = generateRandomPoints(points, y_min, y_max, dur)
    csv_data = exportToCSV(dur, ival, pts, y_min, y_max)
    
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(csv_data)
        if verbose:
            lines = len(csv_data.split('\n'))
            print(f"✓ {lines} lines → {output}")
        return output
    else:
        return csv_data

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', type=float, default=30)
    parser.add_argument('--unit', default='m')
    parser.add_argument('--y-min', type=float, default=0)
    parser.add_argument('--y-max', type=float, default=100)
    parser.add_argument('--interval', type=float, default=1)
    parser.add_argument('--interval-unit', default='s')
    parser.add_argument('--points', type=int, default=61)
    parser.add_argument('--output', default='resources/distributions/traffic_signal.csv')
    parser.add_argument('--seed', type=int, default=None)
    args = parser.parse_args()
    
    generate_traffic_signal(
        duration=args.duration,
        unit=args.unit,
        y_min=args.y_min,
        y_max=args.y_max,
        interval=args.interval,
        interval_unit=args.interval_unit,
        points=args.points,
        output=args.output,
        seed=args.seed
    )
