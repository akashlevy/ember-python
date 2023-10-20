"""Simply abort current operation"""
from ember import EMBERDriver

with EMBERDriver("CHIP", "settings/form.json") as ember:
  ember.abort()