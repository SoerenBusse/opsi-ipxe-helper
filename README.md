# Unofficial OPSI iPXE Boot

An unofficial tool to streamline booting OPSI clients using iPXE, enhanced with several convenient helper functions for a smooth and customizable netboot experience.

## Key Features

- **Create OPSI Clients Directly in iPXE**  
  Seamlessly generate OPSI client configurations without leaving the iPXE environment.

- **Automatic Hardware Identification**  
  Detect MAC addresses and system UUIDs automatically for simple client provisioning.

- **Interactive Product Selection**  
  Choose the netboot product and product group to install directly through the iPXE menu interface.

- **Secure Client Creation**  
  Includes authentication steps before client creation to ensure secure access.

- **Customizable Menus**  
  Easily add additional boot options like `netboot.xyz` through configuration files.

- **Static File Server Support**  
  Serve custom EFI files (e.g., memtest) via a built-in static file server.

![Main Menu](https://github.com/user-attachments/assets/1fe175d0-25bd-45a2-a24e-5c97d65ce543)


![Create Client](https://github.com/user-attachments/assets/8b7f7bb3-8c16-4993-af54-9df5e1e6890f)



# Setup
## Prepare OPSI Server
### Create API user
It is recommended to create a dedicated `opsiapi` user for this tool.  
Adjust the user permissions as needed in `/etc/opsi/backendManager/acl.conf`.
```
adduser opsiapi --ingroup opsiadmin --no-create-home --shell /usr/sbin/nologin
```
## Installation
python3-venv must be installed.
```
# Installation
git clone https://github.com/SoerenBusse/opsi-ipxe-helper.git /opt/opsi-ipxe-helper
cd /opt/opsi-ipxe-helper
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt

# Edit config.yml
cp config.example.yml config.yml

# Setup systemd service
useradd --system --no-create-home --shell /usr/sbin/nologin opsi-ipxe-helper

cp systemd/opsi-ipxe-helper.service /etc/systemd/system/opsi-ipxe-helper.service

systemctl enable opsi-ipxe-helper.service
systemctl start opsi-ipxe-helper.service
```


---

## Development
This project includes a helper script test-ipxe.sh to simplify development and testing. The script builds a custom ipxe.efi binary that automatically fetches boot.ipxe from your development server, eliminating the need for DHCP configuration.

### Build the ipxe.efi.
Replace `<ip-address>` with the IP address reachable from within a QEMU VM (do not use localhost):
```
bash test-ipxe.sh setup <ip-address>:8000
```

### Launch QEMU
Start a QEMU virtual machine using the built ipxe.efi as the startup firmware:
```
bash test-ipxe.sh run
```
