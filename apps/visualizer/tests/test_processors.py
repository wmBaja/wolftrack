import pytest
from src.pipeline.processor import ScaleProcessor, BiasProcessor, FilterProcessor

def test_scale_processor():
    processor = ScaleProcessor("TEST_SIGNAL", 2.0)
    
    # Process method directly
    assert processor.process(10.0) == 20.0
    
    # Signal processing
    msg = {"name": "TEST_SIGNAL", "value": 5.0}
    res = processor(msg)
    assert res["value"] == 10.0
    
    # Ignore unrelated signals
    msg_ignore = {"name": "OTHER_SIGNAL", "value": 5.0}
    res_ignore = processor(dict(msg_ignore))
    assert res_ignore["value"] == 5.0

def test_bias_processor():
    processor = BiasProcessor("TEST_SIGNAL", 5.0)
    
    assert processor.process(10.0) == 15.0
    
    msg = {"name": "TEST_SIGNAL", "value": 5.0}
    res = processor(msg)
    assert res["value"] == 10.0

def test_filter_processor():
    processor = FilterProcessor("TEST_SIGNAL", window_size=3)
    
    assert processor.process(10.0) == 10.0 # [10]
    assert processor.process(20.0) == 15.0 # [10, 20]
    assert processor.process(30.0) == 20.0 # [10, 20, 30]
    assert processor.process(40.0) == 30.0 # [20, 30, 40]
    
    # Test __call__ with window updates
    p2 = FilterProcessor("BATT", window_size=2)
    m1 = p2({"name": "BATT", "value": 10.0})
    assert m1["value"] == 10.0
    
    m2 = p2({"name": "BATT", "value": 20.0})
    assert m2["value"] == 15.0
