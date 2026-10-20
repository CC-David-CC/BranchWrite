abi <abi/5.0>,
include <tunables/global>
profile branchwrite_browser_worker flags=(attach_disconnected,mediate_deleted) {
  allow capability sys_admin sys_chroot,
  allow file rwlkm /{**,},
  allow network,
  allow unix,
  allow ptrace,
  allow signal,
  allow mqueue,
  allow io_uring,
  allow userns,
  allow mount,
  allow umount,
  allow pivot_root,
  allow dbus,
  allow pix /** -> &branchwrite_browser_worker,
}
