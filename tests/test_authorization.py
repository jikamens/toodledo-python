import time

def test_429_error_handling(toodledo):
	"""Confirm that we automatically refresh our authorization
	token after 100 requests."""
	for _ in range(101):
		_ = toodledo.GetAccount()
