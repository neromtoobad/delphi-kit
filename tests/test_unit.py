import warnings


def test_reexports_agon():
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        import delphi_kit
    import agon
    assert delphi_kit.Delphi is agon.Delphi
