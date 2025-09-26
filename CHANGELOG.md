# CHANGELOG

<!-- version list -->

## v14.1.0 (2025-09-26)

### Bug Fixes

- [ESXi] Fix getting Interrupt Moderation Rate for i40en
  ([`fa86cad`](https://github.com/intel/mfd-network-adapter/commit/fa86cad916a704553c593a7f34e660059ba7e6c7))

- DLL copy fix to not overwrite files.
  ([`83b4c47`](https://github.com/intel/mfd-network-adapter/commit/83b4c47b486b636e19d789dfad707d483cabd76e))

- Fix getting ARP table for Linux
  ([`157a026`](https://github.com/intel/mfd-network-adapter/commit/157a0261a10393adc3d522a20096b1cdf7b7d237))

- Query on multiple interfaces with same pci address
  ([`e603af4`](https://github.com/intel/mfd-network-adapter/commit/e603af4d95c2861f7ddc8c10a28ff5ede1f7903a))

- VF interface incorrectly assigned to the BOND_SLAVE category
  ([`eb42da9`](https://github.com/intel/mfd-network-adapter/commit/eb42da92d7fa2de03c623df3fab63ed648e12cb4))

### Continuous Integration

- Update repository name handling in workflows for pull requests
  ([`0873e1d`](https://github.com/intel/mfd-network-adapter/commit/0873e1d75118e7591a80f3ad7f71ee80b2a26f6c))

- Update workflows
  ([`5458d3d`](https://github.com/intel/mfd-network-adapter/commit/5458d3d3ef5212acd19794dcd8707601ba344215))

### Features

- Add GTP functionality
  ([`e76f59e`](https://github.com/intel/mfd-network-adapter/commit/e76f59eba4c705986f0164a3514d6e0220b460ad))

- Add support for Hyper-V Linux VM interfaces - VMNICs
  ([`aa46b99`](https://github.com/intel/mfd-network-adapter/commit/aa46b99f945bc7f53a248624a6e048a4775bac4e))

- Handle ESXi 9.0 in finding VF for a given VM by its ID
  ([`65e01ce`](https://github.com/intel/mfd-network-adapter/commit/65e01cebff38c6f2ffc1153ba71a33a3817158fd))


## v14.0.0 (2025-07-11)

### Features

- Initial commit
  ([`ae14cba`](https://github.com/intel/mfd-network-adapter/commit/ae14cba83b9511a56f00aa7719fa7c8c2779aa8e))

### Breaking Changes

- OIDs binaries removed
