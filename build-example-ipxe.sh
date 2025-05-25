WORKING_DIRECTORY="/tmp/ipxe"

 # Remove working directory
rm -rf "${WORKING_DIRECTORY}"
git clone https://github.com/ipxe/ipxe.git "${WORKING_DIRECTORY}"
cd "${WORKING_DIRECTORY}/src"

sed -i 's/\/\/#define\ PING_CMD/#define\ PING_CMD/' config/general.h
sed -i 's/\/\/#define\ CONSOLE_CMD/#define\ CONSOLE_CMD/' config/general.h
sed -i 's/\/\/#define\ REBOOT_CMD/#define\ REBOOT_CMD/' config/general.h
sed -i 's/\/\/#define\ POWEROFF_CMD/#define\ POWEROFF_CMD/' config/general.h
sed -i 's/\/\/#define\ CONSOLE_FRAMEBUFFER/#define\ CONSOLE_FRAMEBUFFER/' config/console.h

# German Keyboard Layout
sed -i 's/#define\tKEYBOARD_MAP\tus/#define\tKEYBOARD_MAP\tde/' config/console.h

make -j $(nproc --all) bin-x86_64-efi/ipxe.efi
cp bin-x86_64-efi/ipxe.efi "${WORKING_DIRECTORY}/ipxe.efi"