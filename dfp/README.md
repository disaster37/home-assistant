# Pond control

It consume DFP API to manage all pond.

## Switch

```yaml
switch:
  - platform: dfp
    resource: http://IP_ADDRESS
    username: dfp
    password: dfp
    name: DFP
    actions:
      dfp_start_stop:
        name: Start/Stop DFP
        module: dfp
        state: is_running
        turn_on_action: start
        turn_off_action: stop
```

JWT renew: https://betterprogramming.pub/how-to-refresh-an-access-token-using-decorators-981b1b12fcb9