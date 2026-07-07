import os

b = os.path.getsize(r'D:\DroidSentinel\artifacts\after_clear_data\notification_log_before.db')
a = os.path.getsize(r'D:\DroidSentinel\artifacts\after_clear_data\notification_log_after.db')
print(f'notification_log BEFORE: {b} bytes')
print(f'notification_log AFTER:  {a} bytes')
print(f'Difference: {a-b} bytes')