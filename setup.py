import platform
from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup

# Additional C++ binding libraries that you might want to add
_rocv2 = Pybind11Extension(
    "qcmanager.hw._rocv2", sorted(["src/qcmanager/hw/_rocv2.cc"])
)
_rocv2._add_ldflags(["-lboost_serialization"])
if platform.system() == "Darwin":
    _rocv2._add_cflags(
        ["-isysroot", "/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/"]
    )

setup(
    ext_modules=[_rocv2],
    cmdclass={"build_ext": build_ext},
)
