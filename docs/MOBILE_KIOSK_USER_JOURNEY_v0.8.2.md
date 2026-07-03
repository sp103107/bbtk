# Mobile Kiosk User Journey v0.8.2

## Gold path

```text
Open local network URL
↓
Confirm backend status
↓
Enter employee ID
↓
Enter PIN
↓
Tap Clock In / Clock Out / Break
↓
Read receipt
↓
Confirm Today's Hours and Current Status
```

## Backend interruption path

```text
Backend drops
↓
UI shows backend not connected
↓
Employee can save local recovery evidence
↓
Offline queue shows pending sync
↓
Owner later syncs and reviews
```

## Design law

The employee screen must not become an owner console. Employee flow stays one-screen and low-noise.
