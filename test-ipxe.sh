#!/bin/bash
set -e

WORKING_DIRECTORY="/tmp/ipxe"
EMBED_FILE="${WORKING_DIRECTORY}/embed.ipxe"

action="${1}"

if [[ -z "$action" ]]; then
  echo "${0} <setup/run>"
  exit 1
fi

if [[ "$action" == "setup" ]]; then
  server="${2}"
  if [[ -z "${server}" ]]; then
    echo "${0} setup <server>"
    exit 1
  fi

  # Remove working directory
  rm -rf "${WORKING_DIRECTORY}"
  git clone https://github.com/ipxe/ipxe.git "${WORKING_DIRECTORY}"
  cd "${WORKING_DIRECTORY}/src"

  # Update config
  sed -i 's/\/\/#define\ PING_CMD/#define\ PING_CMD/' config/general.h
  sed -i 's/\/\/#define\ CONSOLE_CMD/#define\ CONSOLE_CMD/' config/general.h
  sed -i 's/\/\/#define\ REBOOT_CMD/#define\ REBOOT_CMD/' config/general.h
  sed -i 's/\/\/#define\ POWEROFF_CMD/#define\ POWEROFF_CMD/' config/general.h
  sed -i 's/#undef[[:space:]]\+DOWNLOAD_PROTO_HTTPS/#define DOWNLOAD_PROTO_HTTPS/' config/general.h
  sed -i 's/\/\/#define\ CONSOLE_FRAMEBUFFER/#define\ CONSOLE_FRAMEBUFFER/' config/console.h

  # Good enough ;)
  sed -i 's/us/de/' config/console.h

  # Create IPXE config
  echo '#!ipxe' >> "${EMBED_FILE}"
  echo 'set esc:hex 1b' >> "${EMBED_FILE}"
  echo 'set cls ${esc:string}[2J' >> "${EMBED_FILE}"
  echo 'echo ${cls}' >> "${EMBED_FILE}"
  echo "dhcp" >> "${EMBED_FILE}"
  echo "chain http://${server}/boot || shell" >> "${EMBED_FILE}"
  # Compile
  make -j $(nproc --all) bin-x86_64-efi/ipxe.efi EMBED="${EMBED_FILE}"
  cp bin-x86_64-efi/ipxe.efi "${WORKING_DIRECTORY}/ipxe.efi"

  exit 0
fi

if [[ "$action" == "run" ]]; then
  # Start QEMU with IPXE image
  qemu-system-x86_64 \
    -enable-kvm \
    -m 2048 \
    -bios /usr/share/OVMF/OVMF_CODE.fd \
    -kernel "${WORKING_DIRECTORY}/ipxe.efi" \
    -netdev user,id=net0 \
    -device virtio-net-pci,netdev=net0 \
    -uuid 58248384-b0e7-41c7-bd00-dba3c408a8a6
  exit 0
fi

echo "Invalid action ${action}"
exit 1
