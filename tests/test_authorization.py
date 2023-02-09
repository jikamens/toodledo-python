# This test is currently commented out because it takes a long time and it's
# not necessary because the full test suite is guaranteed to get rate-limited
# so we don't need a separate test for that.

# import time
#
# def test_429_error_handling(toodledo):
#     """Confirm that we automatically refresh our authorization
#     token after 100 requests."""
#     for _ in range(101):
#         _ = toodledo.GetAccount()
