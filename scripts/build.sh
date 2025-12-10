pip3 download pillow --dest ./wheels --only-binary=:all: --python-version=3.11 --platform=manylinux_2_28_x86_64
pip3 download pillow --dest ./wheels --only-binary=:all: --python-version=3.11 --platform=macosx_10_10_x86_64
pip3 download pillow --dest ./wheels --only-binary=:all: --python-version=3.11 --platform=win_amd64
blender --command extension build --split-platforms