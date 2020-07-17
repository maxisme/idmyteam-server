import base64

import pytest
from utils import functions
from Crypto import Random

test_strings = [
    ("A" * 1000),
    ("."),
    ("abcdefg" * 1000),
    ("d"),
    ("6**))%@19hhjh_-{}[]'gg66g"),
    ("test"),
]


@pytest.mark.parametrize("input", test_strings)
def test_encrypt(input):
    key = base64.b64encode(Random.new().read(32))

    cipher = functions.AESCipher(key)
    encrypt = cipher.encrypt(input)
    assert cipher.decrypt(encrypt) == input


@pytest.mark.parametrize("input", test_strings)
def test_compress_str(input):
    assert functions.decompress_string(functions.compress_string(input)) == input


@pytest.mark.parametrize("input", test_strings)
def test_hash_pw(input):
    hash = functions.hash_pw(input)
    assert len(hash) == 60
    assert functions.check_pw_hash(input, hash) == True


@pytest.mark.parametrize("input", test_strings)
def test_hash(input):
    assert len(functions.hash(input)) == 64


test_crop_array_dict = {
    "foo": ["1.jpg", "2.jpg", "3.jpg"],
    "bar": ["1.jpg", "2.jpg", "3.jpg", "4.jpg", "5.jpg"],
    "baz": ["1.jpg", "2.jpg", "3.jpg", "4.jpg"],
}


@pytest.mark.parametrize(
    "dict,num,expected",
    [
        (  # test 1
            test_crop_array_dict,
            4,
            {"foo": ["1.jpg", "2.jpg"], "bar": ["1.jpg"], "baz": ["1.jpg"]},
        ),
        (test_crop_array_dict, 0, {}),  # test 2
        ({}, 0, {}),  # test 3
        (  # test 4
            test_crop_array_dict,
            5,
            {"foo": ["1.jpg", "2.jpg"], "bar": ["1.jpg", "2.jpg"], "baz": ["1.jpg"]},
        ),
        (  # test 5
            test_crop_array_dict,
            8,
            {
                "foo": ["1.jpg", "2.jpg", "3.jpg"],
                "bar": ["1.jpg", "2.jpg", "3.jpg"],
                "baz": ["1.jpg", "2.jpg"],
            },
        ),
        (test_crop_array_dict, 100000, test_crop_array_dict),  # test 6
    ],
)
def test_crop_array(dict, num, expected):
    assert functions.crop_arr(dict, num) == expected
