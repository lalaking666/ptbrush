import pytest
from ptbrush.config.config import parse_size, parse_speed, BrushConfig, parse_time_ranges
from datetime import time, datetime
from unittest.mock import patch
from ptbrush.main import check_work_time

def test_parse_size():
    # Test integer input
    assert parse_size(1024) == 1024
    assert parse_size("1024") == 1024
    
    # Test binary units
    assert parse_size("1KiB") == 1024
    assert parse_size("1MiB") == 1024 * 1024
    assert parse_size("1GiB") == 1024 * 1024 * 1024
    assert parse_size("1TiB") == 1024 * 1024 * 1024 * 1024
    
    # Test decimal units
    assert parse_size("1KB") == 1000
    assert parse_size("1MB") == 1000 * 1000
    assert parse_size("1GB") == 1000 * 1000 * 1000
    assert parse_size("1TB") == 1000 * 1000 * 1000 * 1000
    
    # Test float values
    assert parse_size("1.5GiB") == int(1.5 * 1024 * 1024 * 1024)
    
    # Test invalid inputs
    with pytest.raises(ValueError):
        parse_size("invalid")
    with pytest.raises(ValueError):
        parse_size("1XB")
    with pytest.raises(ValueError):
        parse_size("-1GiB")

def test_parse_speed():
    # Test integer input
    assert parse_speed(1024) == 1024
    assert parse_speed("1024") == 1024
    
    # Test units
    assert parse_speed("1KiB/s") == 1024
    assert parse_speed("1MiB/s") == 1024 * 1024
    assert parse_speed("1GiB/s") == 1024 * 1024 * 1024
    
    # Test float values
    assert parse_speed("1.5MiB/s") == int(1.5 * 1024 * 1024)
    
    # Test invalid inputs
    with pytest.raises(ValueError):
        parse_speed("invalid")
    with pytest.raises(ValueError):
        parse_speed("1MB/s")  # Only binary units allowed
    with pytest.raises(ValueError):
        parse_speed("-1MiB/s")

def test_brush_config():
    # Test valid config
    config = BrushConfig(
        min_disk_space="1024GiB",
        expect_upload_speed="1.875MiB/s",
        expect_download_speed="12MiB/s",
        torrent_max_size="50GiB"
    )
    assert config.min_disk_space == 1024 * 1024 * 1024 * 1024
    assert config.expect_upload_speed == int(1.875 * 1024 * 1024)
    assert config.expect_download_speed == 12 * 1024 * 1024
    assert config.torrent_max_size == 50 * 1024 * 1024 * 1024
    
    # Test invalid configs
    with pytest.raises(ValueError):
        BrushConfig(min_disk_space="invalid")
    
    with pytest.raises(ValueError):
        BrushConfig(expect_upload_speed="30Mbps")  # No longer supported
    
    with pytest.raises(ValueError):
        BrushConfig(expect_download_speed="100MB/s")  # Only binary units allowed
    
    with pytest.raises(ValueError):
        BrushConfig(torrent_max_size="-50GiB")

def test_brush_config_defaults():
    config = BrushConfig()
    # Test default values
    assert config.min_disk_space == 1024 * 1024 * 1024 * 1024  # 1024 GiB
    assert config.expect_upload_speed == int(1.875 * 1024 * 1024)  # 1.875 MiB/s
    assert config.expect_download_speed == 12 * 1024 * 1024  # 12 MiB/s
    assert config.torrent_max_size == 50 * 1024 * 1024 * 1024  # 50 GiB
    assert config.max_downloading_torrents == 6
    assert config.upload_cycle == 600
    assert config.download_cycle == 600
    assert config.max_no_activate_time == 24 

def test_parse_time_ranges():
    # Test single range
    ranges = parse_time_ranges("1-4")
    assert len(ranges) == 1
    assert ranges[0] == (time(hour=1), time(hour=4, minute=59, second=59))
    
    # Test multiple ranges
    ranges = parse_time_ranges("20-23,0-6")
    assert len(ranges) == 2
    assert ranges[0] == (time(hour=20), time(hour=23, minute=59, second=59))
    assert ranges[1] == (time(hour=0), time(hour=6, minute=59, second=59))
    
    # Test empty string
    assert parse_time_ranges("") == []
    
    # Test invalid formats
    with pytest.raises(ValueError):
        parse_time_ranges("1-24")  # Invalid hour
    with pytest.raises(ValueError):
        parse_time_ranges("1-4-5")  # Invalid format
    with pytest.raises(ValueError):
        parse_time_ranges("aa-bb")  # Invalid format

def test_work_time_validation():
    # Test valid work times
    config = BrushConfig(work_time="1-4")
    assert config.work_time == "1-4"
    
    config = BrushConfig(work_time="20-23,0-6")
    assert config.work_time == "20-23,0-6"
    
    config = BrushConfig(work_time="")  # Empty string is valid
    assert config.work_time == ""
    
    # Test invalid work times
    with pytest.raises(ValueError):
        BrushConfig(work_time="25-26")  # Invalid hours
    with pytest.raises(ValueError):
        BrushConfig(work_time="1-4-5")  # Invalid format 

def test_check_work_time(mocker):
    # Mock datetime.now() to control the current time
    class MockDateTime:
        @classmethod
        def now(cls):
            return cls.current_time
    
    # Test when work_time is empty (24h mode)
    mock_config = mocker.Mock()
    mock_config.brush = BrushConfig(work_time="")
    mocker.patch('ptbrush.config.config.PTBrushConfig', return_value=mock_config)
    assert check_work_time(mock_config.brush) == True
    
    # Test when current time is within work hours
    mock_config.brush = BrushConfig(work_time="1-4")
    
    # Set current time to 2:30
    MockDateTime.current_time = datetime(2024, 1, 1, 2, 30)
    with patch('ptbrush.config.config.datetime', MockDateTime):
        assert check_work_time(mock_config.brush) == True
    
    # Test when current time is outside work hours
    # Set current time to 5:00
    MockDateTime.current_time = datetime(2024, 1, 1, 5, 0)
    with patch('ptbrush.config.config.datetime', MockDateTime):
        assert check_work_time(mock_config.brush) == False
    
    # Test multiple time ranges
    mock_config.brush = BrushConfig(work_time="20-23,0-6")
    
    # Test time within first range (21:00)
    MockDateTime.current_time = datetime(2024, 1, 1, 21, 0)
    with patch('ptbrush.config.config.datetime', MockDateTime):
        assert check_work_time(mock_config.brush) == True
    
    # Test time within second range (3:00)
    MockDateTime.current_time = datetime(2024, 1, 1, 3, 0)
    with patch('ptbrush.config.config.datetime', MockDateTime):
        assert check_work_time(mock_config.brush) == True
    
    # Test time outside both ranges (12:00)
    MockDateTime.current_time = datetime(2024, 1, 1, 12, 0)
    with patch('ptbrush.config.config.datetime', MockDateTime):
        assert check_work_time(mock_config.brush) == False
    
    # Test edge cases
    # Start of range
    MockDateTime.current_time = datetime(2024, 1, 1, 20, 0)
    with patch('ptbrush.config.config.datetime', MockDateTime):
        assert check_work_time(mock_config.brush) == True
    
    # End of range
    MockDateTime.current_time = datetime(2024, 1, 1, 23, 59)
    with patch('ptbrush.config.config.datetime', MockDateTime):
        assert check_work_time(mock_config.brush) == True
    
    # Just outside range
    MockDateTime.current_time = datetime(2024, 1, 1, 19, 59)
    with patch('ptbrush.config.config.datetime', MockDateTime):
        assert check_work_time(mock_config.brush) == False 