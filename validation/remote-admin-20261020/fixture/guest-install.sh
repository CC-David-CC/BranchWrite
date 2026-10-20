set -eu
export DEBIAN_FRONTEND=noninteractive
TARGET=/mnt/bw-install
printf 'PHASE guard-owned-blank-disk\n'
test "$(blockdev --getsize64 /dev/vda)" = 34359738368
test "$(readlink -f /sys/block/vda/device/driver | sed 's|.*/||')" = virtio_blk
test -z "$(wipefs -n --noheadings /dev/vda)"
test ! -e /sys/block/vda/vda1
test -f /cdrom/casper/filesystem.squashfs
mkdir -p "$TARGET"
! mountpoint -q "$TARGET"
printf 'PHASE partition-format\n'
parted -s /dev/vda mklabel gpt
parted -s /dev/vda mkpart ESP fat32 1MiB 513MiB
parted -s /dev/vda set 1 esp on
parted -s /dev/vda mkpart root ext4 513MiB 100%
udevadm settle
mkfs.fat -F 32 -n BW_EFI /dev/vda1
fsck.fat -n /dev/vda1
mkfs.ext4 -F -L bw-admin-root /dev/vda2
mount /dev/vda2 "$TARGET"
printf 'PHASE extract-installed-root\n'
unsquashfs -f -no-progress -processors 4 -d "$TARGET" /cdrom/casper/filesystem.squashfs
printf 'PHASE persist-identity-network-ssh\n'
for name in passwd shadow group gshadow sudoers machine-id; do cp -a "/etc/$name" "$TARGET/etc/$name"; done
rsync -a /etc/ssh/ "$TARGET/etc/ssh/"
rsync -a /etc/sudoers.d/ "$TARGET/etc/sudoers.d/"
rsync -a /etc/netplan/ "$TARGET/etc/netplan/"
install -d -m 700 -o 1000 -g 1000 "$TARGET/home/maint/.ssh"
install -m 600 -o 1000 -g 1000 /home/maint/.ssh/authorized_keys "$TARGET/home/maint/.ssh/authorized_keys"
printf 'branchwrite-admin01\n' > "$TARGET/etc/hostname"
printf '127.0.0.1 localhost\n127.0.1.1 branchwrite-admin01\n::1 localhost ip6-localhost ip6-loopback\n' > "$TARGET/etc/hosts"
ROOT_UUID=$(blkid -s UUID -o value /dev/vda2)
EFI_UUID=$(blkid -s UUID -o value /dev/vda1)
printf 'UUID=%s / ext4 defaults 0 1\nUUID=%s /boot/efi vfat umask=0077 0 1\n' "$ROOT_UUID" "$EFI_UUID" > "$TARGET/etc/fstab"
mkdir -p "$TARGET/boot/efi" "$TARGET/dev" "$TARGET/proc" "$TARGET/sys" "$TARGET/run"
mount /dev/vda1 "$TARGET/boot/efi"
for name in dev proc sys run; do mount --rbind "/$name" "$TARGET/$name"; mount --make-rslave "$TARGET/$name"; done
printf '#!/bin/sh\nexit 101\n' > "$TARGET/usr/sbin/policy-rc.d"
chmod 755 "$TARGET/usr/sbin/policy-rc.d"
printf 'PHASE remove-live-boot-package\n'
chroot "$TARGET" apt-get -y purge casper
printf 'PHASE install-efi-bootloader\n'
chroot "$TARGET" update-initramfs -u -k all
chroot "$TARGET" grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=BranchWrite --removable --no-nvram --recheck
chroot "$TARGET" update-grub
chroot "$TARGET" systemctl enable ssh.service NetworkManager.service
rm "$TARGET/usr/sbin/policy-rc.d"
printf 'PHASE verify-installed-root\n'
test -s "$TARGET/boot/efi/EFI/BOOT/BOOTX64.EFI"
test -s "$TARGET/boot/grub/grub.cfg"
test -s "$TARGET/boot/initrd.img-7.0.14-codiserver-base"
test -s "$TARGET/home/maint/.ssh/authorized_keys"
chroot "$TARGET" visudo -c
sync
umount -R "$TARGET"
sync
printf 'PHASE installed-ready-for-disk-boot\n'
