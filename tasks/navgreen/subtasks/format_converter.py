#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict

def convert_zoom_to_windy_format(zoom_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Zoom.Earth typhoon data format to Windy format
    
    Args:
        zoom_data (dict): Typhoon data in Zoom.Earth format
        
    Returns:
        dict: Typhoon data in Windy format
    """
    # Extract basic info
    typhoon_data = {
        'id': zoom_data['id'],
        'name': zoom_data['name'],
        'lat': None,  # Will be updated with latest position
        'lon': None,  # Will be updated with latest position
        'strength': 1,  # Default value as it's not directly mappable
        'windSpeed': None,  # Will be updated with latest wind speed
        'history': [],
        'forecast': []
    }
    
    result = {
        'data': [typhoon_data],
        'fresh_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Process track points
    current_time = None
    forecast_points = defaultdict(list)  # Group forecast points by reference time
    
    for point in zoom_data['track']:
        # Extract common fields
        point_data = {
            'lat': point['coordinates'][1],  # Zoom uses [lon, lat]
            'lon': point['coordinates'][0],
            'windSpeed': point['wind'] * 0.514444,  # Convert knots to m/s
            'pressure': point['pressure'] if point['pressure'] else None,
            'time': point['date']
        }
        
        # Update latest position if this is the most recent non-forecast point
        if not point['forecast'] and (current_time is None or point['date'] > current_time):
            current_time = point['date']
            typhoon_data['lat'] = point_data['lat']
            typhoon_data['lon'] = point_data['lon']
            typhoon_data['windSpeed'] = point_data['windSpeed']
            
        # Add to appropriate list
        if point['forecast']:
            # Group forecast points by their reference time (current_time)
            forecast_points[current_time].append(point_data)
        else:
            typhoon_data['history'].append(point_data)
    
    # Convert forecast points into the required format
    if forecast_points:
        for reftime, points in forecast_points.items():
            forecast_entry = {
                'reftime': reftime,
                'modelIdentifier': 'zoom',  # Using 'zoom' as the model identifier
                'records': sorted(points, key=lambda x: x['time'])
            }
            typhoon_data['forecast'].append(forecast_entry)
            
    # Sort history by time in descending order (newest first)
    typhoon_data['history'].sort(key=lambda x: x['time'], reverse=True)
    
    return result

def test_converter():
    """Test function to verify the converter works correctly"""
    # Example Zoom.Earth format data
    zoom_data = {
        'id': 'nari-2025',
        'name': 'Nari',
        'track': [
            {
                'date': '2025-07-14T12:00:00Z',
                'coordinates': [142.5, 39.7],
                'wind': 40,
                'pressure': 985,
                'forecast': False
            },
            {
                'date': '2025-07-15T00:00:00Z',
                'coordinates': [145.4, 44.9],
                'wind': 35,
                'pressure': None,
                'forecast': True
            }
        ]
    }
    
    # Convert and print result
    result = convert_zoom_to_windy_format(zoom_data)
    print("Converted data:", result)

if __name__ == "__main__":
    test_converter() 