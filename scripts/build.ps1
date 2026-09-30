pip3.exe download pillow==12.3.0 --dest .\wheels --only-binary=:all: --python-version=3.13 --platform=manylinux_2_28_x86_64
pip3.exe download pillow==12.3.0 --dest .\wheels --only-binary=:all: --python-version=3.13 --platform=manylinux_2_28_aarch64
pip3.exe download pillow==12.3.0 --dest .\wheels --only-binary=:all: --python-version=3.13 --platform=macosx_11_0_arm64
pip3.exe download pillow==12.3.0 --dest .\wheels --only-binary=:all: --python-version=3.13 --platform=win_amd64
pip3.exe download pillow==12.3.0 --dest .\wheels --only-binary=:all: --python-version=3.13 --platform=win_arm64
blender.exe --command extension build --split-platforms --output-dir .\build
