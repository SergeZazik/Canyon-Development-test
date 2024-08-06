from datetime import datetime
import json
import os


#Parse Input Files
#----------------------------------------------------------------------------------------------------------------#
def parse_json_file(file_path):
    """Parses a JSON file and returns the data."""
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
        return data
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error reading JSON file {file_path}: {e}")
        return None

def parse_pos_file(file_path):
    """Parses a .pos file and returns a list of (timestamp, latitude, longitude) tuples."""
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
    except IOError as e:
        print(f"Error reading .pos file {file_path}: {e}")
        return None

    data_start_index = next((i + 1 for i, line in enumerate(lines) if line.startswith('%  GPST')), None)
    if data_start_index is None:
        print(f"No data start marker found in file {file_path}")
        return []
    
    pos_data = []
    for line in lines[data_start_index:]:
        if line.startswith('%') or not line.strip():
            continue
        parts = line.split()
        timestamp = date_str_to_timestamp(datetime.strptime(f"{parts[0]} {parts[1]}", "%Y/%m/%d %H:%M:%S.%f"))
        latitude = float(parts[2])
        longitude = float(parts[3])
        pos_data.append((timestamp, latitude, longitude))
    
    return pos_data

def date_str_to_timestamp(dt):
    """Converts a datetime object to a timestamp with nanoseconds."""
    timestamp_seconds = dt.timestamp()
    microseconds = dt.microsecond
    nanoseconds = microseconds * 1000
    timestamp_with_nanoseconds = int(timestamp_seconds * 1e9) + nanoseconds
    return timestamp_with_nanoseconds
#----------------------------------------------------------------------------------------------------------------#


#Associate Timestamps with GPS Coordinates
#----------------------------------------------------------------------------------------------------------------#
def find_closest_timestamp(pos_data, target_timestamp):
    """Find the closest timestamp in pos_data to the target_timestamp."""
    closest = min(pos_data, key=lambda x: abs(x[0] - target_timestamp))
    return closest[1], closest[2]

def associate_timestamps_with_gps(json_data, pos_data):
    """Associate each timestamp in json_data with the closest GPS coordinates from pos_data."""
    associations = []
    for frame in json_data['timestamps']:
        frame_index = frame[0]
        frame_timestamp = frame[1]
        latitude, longitude = find_closest_timestamp(pos_data, frame_timestamp)
        associations.append({
            'index': frame_index,
            'timestamp': frame_timestamp,
            'latitude': latitude,
            'longitude': longitude
        })
    return associations
#----------------------------------------------------------------------------------------------------------------#


#Calculate Centroid
#----------------------------------------------------------------------------------------------------------------#
def calculate_centroid(locations):
    if not locations:
        raise ValueError("The list of locations is empty")
    
    if not all('latitude' in loc and 'longitude' in loc for loc in locations):
        raise ValueError("Each location must have 'latitude' and 'longitude' keys")
    
    latitudes = [loc['latitude'] for loc in locations]
    longitudes = [loc['longitude'] for loc in locations]
    
    if not latitudes or not longitudes:
        raise ValueError("Latitude and longitude lists cannot be empty")
    
    centroid_lat = sum(latitudes) / len(latitudes)
    centroid_lon = sum(longitudes) / len(longitudes)
    return centroid_lat, centroid_lon
#----------------------------------------------------------------------------------------------------------------#


#Generate GeoJSON Output
#----------------------------------------------------------------------------------------------------------------#
def generate_geojson_output(json_data, associations, centroid):
    """Generate a GeoJSON output from the provided data."""
    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [assoc['longitude'], assoc['latitude']]
            },
            "properties": {
                "index": assoc['index'],
                "timestamp": assoc['timestamp']
            }
        }
        for assoc in associations
    ]

    geojson = {
        "type": "FeatureCollection",
        "filename": json_data.get('filename', ''),
        "device_alias": json_data.get('device_alias', ''),
        "total": json_data.get('total', 0),
        "beginning": json_data.get('beginning', ''),
        "end": json_data.get('end', ''),
        "centroid": {
            "lat": centroid[0],
            "lon": centroid[1]
        },
        "features": features
    }
    
    return geojson

def write_geojson_file(filepath, geojson):
    """Write the GeoJSON data to a file."""
    try:
        with open(filepath, 'w') as file:
            json.dump(geojson, file, indent=4)
    except IOError as e:
        print(f"An error occurred while writing the file: {e}")
#----------------------------------------------------------------------------------------------------------------#


#Main Function
#----------------------------------------------------------------------------------------------------------------#
def process_files(folder, output_file: str = 'geojson'):
    files = os.listdir(folder)
    json_files = [(index, os.path.join(folder, file)) for index, file in enumerate(files) if file.endswith('.json')]
    pos_file = next((os.path.join(folder, file) for file in files if file.endswith('.pos')), None)

    if pos_file is None:
        raise FileNotFoundError("No .pos file found in the folder.")
    
    pos_data = parse_pos_file(pos_file)

    for index, json_file in json_files:
        json_data = parse_json_file(json_file)
        associations = associate_timestamps_with_gps(json_data, pos_data)
        centroid = calculate_centroid(associations)
        geojson = generate_geojson_output(json_data, associations, centroid)
        write_geojson_file(f"{output_file}_{index}.json", geojson)
#----------------------------------------------------------------------------------------------------------------#


if __name__ == "__main__":
    folder_name = 'CANYON_Python_Task2_Attachment'
    process_files(folder_name)