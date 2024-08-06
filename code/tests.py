import unittest
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime
import json
import os

from main import (
    associate_timestamps_with_gps, 
    calculate_centroid,
    date_str_to_timestamp,
    find_closest_timestamp, 
    generate_geojson_output, 
    parse_json_file, 
    parse_pos_file,
    process_files,
    write_geojson_file,
)


class TestGeoJsonProcessor(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open, read_data='{"timestamps": [[0, 1551949886217313489]], "device_alias": "CAM134", "end": 1551949946552588582, "beginning": 1551949886217313489, "filename": "P_G_07032019_SG_1_1_1_CAM134_110814_RAW_seg4.svo", "total": 480}')
    def test_parse_json_file(self, mock_file):
        file_path = "test.json"
        expected_data = {
            "timestamps": [[0, 1551949886217313489]],
            "device_alias": "CAM134",
            "end": 1551949946552588582,
            "beginning": 1551949886217313489,
            "filename": "P_G_07032019_SG_1_1_1_CAM134_110814_RAW_seg4.svo",
            "total": 480
        }
        data = parse_json_file(file_path)
        self.assertEqual(data, expected_data)

    @patch("builtins.open", new_callable=mock_open, read_data="%  GPST ...\n2024/01/01 00:00:00.000 40.712776 -74.005974\n2024/01/01 00:01:00.000 40.712776 -74.005974\n")
    def test_parse_pos_file(self, mock_file):
        file_path = "test.pos"
        expected_data = [
            (1704060000000000000, 40.712776, -74.005974),
            (1704060060000000000, 40.712776, -74.005974)
        ]
        data = parse_pos_file(file_path)
        self.assertEqual(data, expected_data)

    def test_date_str_to_timestamp(self):
        dt = datetime.strptime("2024/01/01 00:00:00.000", "%Y/%m/%d %H:%M:%S.%f")
        expected_timestamp = 1704060000000000000
        timestamp = date_str_to_timestamp(dt)
        self.assertEqual(timestamp, expected_timestamp)

    def test_find_closest_timestamp(self):
        pos_data = [
            (1577836800000000000, 40.712776, -74.005974),
            (1577836860000000000, 40.712776, -74.005974)
        ]
        target_timestamp = 1577836830000000000
        expected_coords = (40.712776, -74.005974)
        coords = find_closest_timestamp(pos_data, target_timestamp)
        self.assertEqual(coords, expected_coords)

    def test_associate_timestamps_with_gps(self):
        json_data = {
            "timestamps": [[0, 1577836800000000000], [1, 1577836860000000000]]
        }
        pos_data = [
            (1577836800000000000, 40.712776, -74.005974),
            (1577836860000000000, 40.712776, -74.005974)
        ]
        expected_associations = [
            {'index': 0, 'timestamp': 1577836800000000000, 'latitude': 40.712776, 'longitude': -74.005974},
            {'index': 1, 'timestamp': 1577836860000000000, 'latitude': 40.712776, 'longitude': -74.005974}
        ]
        associations = associate_timestamps_with_gps(json_data, pos_data)
        self.assertEqual(associations, expected_associations)

    def test_calculate_centroid(self):
        locations = [
            {'latitude': 40.712776, 'longitude': -74.005974},
            {'latitude': 40.712776, 'longitude': -74.005974}
        ]
        expected_centroid = (40.712776, -74.005974)
        centroid = calculate_centroid(locations)
        self.assertEqual(centroid, expected_centroid)

    def test_generate_geojson_output(self):
        json_data = {
            "filename": "test.json",
            "device_alias": "device1",
            "total": 100,
            "beginning": "2024-01-01T00:00:00Z",
            "end": "2024-01-01T01:00:00Z",
            "timestamps": [[0, 1577836800000000000], [1, 1577836860000000000]]
        }
        associations = [
            {'index': 0, 'timestamp': 1577836800000000000, 'latitude': 40.712776, 'longitude': -74.005974},
            {'index': 1, 'timestamp': 1577836860000000000, 'latitude': 40.712776, 'longitude': -74.005974}
        ]
        centroid = (40.712776, -74.005974)
        expected_geojson = {
            "type": "FeatureCollection",
            "filename": "test.json",
            "device_alias": "device1",
            "total": 100,
            "beginning": "2024-01-01T00:00:00Z",
            "end": "2024-01-01T01:00:00Z",
            "centroid": {
                "lat": 40.712776,
                "lon": -74.005974
            },
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [-74.005974, 40.712776]
                    },
                    "properties": {
                        "index": 0,
                        "timestamp": 1577836800000000000
                    }
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [-74.005974, 40.712776]
                    },
                    "properties": {
                        "index": 1,
                        "timestamp": 1577836860000000000
                    }
                }
            ]
        }
        geojson = generate_geojson_output(json_data, associations, centroid)
        self.assertEqual(geojson, expected_geojson)

    @patch("builtins.open", new_callable=mock_open)
    def test_write_geojson_file(self, mock_file):
        filepath = "output.json"
        geojson = {
            "type": "FeatureCollection",
            "features": []
        }
        write_geojson_file(filepath, geojson)
        mock_file_handle = mock_file()
        written_data = "".join([call.args[0] for call in mock_file_handle.write.mock_calls])
        self.assertEqual(written_data, json.dumps(geojson, indent=4))

    @patch("os.listdir", return_value=['file1.json', 'file2.json', 'file.pos'])
    @patch("main.parse_json_file", return_value={"timestamps": [[0, 1577836800000000000], [1, 1577836860000000000]]})
    @patch("main.parse_pos_file", return_value=[(1577836800000000000, 40.712776, -74.005974), (1577836860000000000, 40.712776, -74.005974)])
    @patch("main.associate_timestamps_with_gps", return_value=[{'index': 0, 'timestamp': 1577836800000000000, 'latitude': 40.712776, 'longitude': -74.005974}, {'index': 1, 'timestamp': 1577836860000000000, 'latitude': 40.712776, 'longitude': -74.005974}])
    @patch("main.calculate_centroid", return_value=(40.712776, -74.005974))
    @patch("main.generate_geojson_output", return_value={"type": "FeatureCollection", "features": []})
    @patch("main.write_geojson_file")
    def test_process_files(self, mock_write_geojson_file, mock_generate_geojson_output, mock_calculate_centroid, mock_associate_timestamps_with_gps, mock_parse_pos_file, mock_parse_json_file, mock_listdir):
        folder = "folder"
        process_files(folder)
        mock_parse_pos_file.assert_called_once()
        self.assertEqual(mock_parse_json_file.call_count, 2)
        self.assertEqual(mock_associate_timestamps_with_gps.call_count, 2)
        self.assertEqual(mock_calculate_centroid.call_count, 2)
        self.assertEqual(mock_generate_geojson_output.call_count, 2)
        self.assertEqual(mock_write_geojson_file.call_count, 2)


if __name__ == "__main__":
    unittest.main()

