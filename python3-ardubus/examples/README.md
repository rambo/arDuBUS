# Examples

Some examples in using the library

Step 0 is always to make a [virtualenv][venvw] and install the library, try

    mkvirtualenv -p `which python3.5` ardubus3
    pip install -e ../

[venvw]: https://virtualenvwrapper.readthedocs.io/en/latest/

## naive.py

Trivial "eventloop" that reads gauge signals and updates their internal positions,
then sends the new values to hardware.

    workon ardubus3
    python3 naive.py /dev/ttyUSB0 ../../python/devices.yml.example 

