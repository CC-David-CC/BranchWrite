set -eu
TARGET=/mnt/bw-install
test "$(findmnt -n -o SOURCE "$TARGET")" = /dev/vda2
sha256sum "$TARGET/boot/efi/EFI/BOOT/BOOTX64.EFI"
cp -a "$TARGET/boot/efi/EFI/BOOT/BOOTX64.EFI" "$TARGET/boot/efi/EFI/BOOT/BOOTX64.EFI.before-repair"
for name in dev proc sys run; do mount --rbind "/$name" "$TARGET/$name"; mount --make-rslave "$TARGET/$name"; done
chroot "$TARGET" grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=BranchWrite --removable --no-nvram --no-uefi-secure-boot --recheck
sha256sum "$TARGET/boot/efi/EFI/BOOT/BOOTX64.EFI"
sync
umount -R "$TARGET"
sync
