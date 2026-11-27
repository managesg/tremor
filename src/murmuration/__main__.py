"""`python -m murmuration` still works: it runs `python -m tremor`."""
import runpy

runpy.run_module("tremor", run_name="__main__", alter_sys=True)
