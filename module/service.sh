#!/system/bin/sh
export PATH=/system/bin:/system/xbin:/sbin:$PATH
( until [ "$(getprop sys.boot_completed)" = "1" ]; do sleep 3; done
  sleep 8
  # perf floors only while screen is awake; stock values when sleeping
  # NOTE: tablet 2 needed cpu_device/sysfs file open perms; plain "r w" was refused
  # by this kernel's SELinux. Keep open read write.
  magiskpolicy --live "allow magisk sysfs file { open read write }" 2>/dev/null
  magiskpolicy --live "allow magisk sysfs_devices_system_cpu file { open read write }" 2>/dev/null
  magiskpolicy --live "allow magisk cpu_device file { open read write }" 2>/dev/null
  apply_state() {
    if [ "$1" = "on" ]; then
      echo 614400000 > /sys/class/devfreq/60000000.gpu/min_freq
      for c in 0 4 5; do echo 1228800 > /sys/devices/system/cpu/cpu$c/cpufreq/scaling_min_freq; done
    else
      echo 384000000 > /sys/class/devfreq/60000000.gpu/min_freq
      for c in 0 4 5; do echo 614400 > /sys/devices/system/cpu/cpu$c/cpufreq/scaling_min_freq; done
    fi
  }
  last=""
  while true; do
    if dumpsys power 2>/dev/null | grep -q "mWakefulness=Awake"; then st=on; else st=off; fi
    if [ "$st" != "$last" ]; then apply_state "$st"; last="$st"; fi
    sleep 3
  done
) &
( until [ "$(getprop sys.boot_completed)" = "1" ]; do sleep 3; done
  sleep 15
  MODDIR=$(dirname "$0")
  while read -r pkg; do
    if pm list packages --user 0 "$pkg" | grep -q "package:$pkg"; then
      pm uninstall -k --user 0 "$pkg"
    fi
  done < "$MODDIR/packages.txt"
  cmd package set-home-activity --user 0 app.lawnchair/.LawnchairLauncher 2>/dev/null
) &
