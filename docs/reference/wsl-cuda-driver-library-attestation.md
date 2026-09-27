# WSL CUDA driver library identity attestation

Issue #3015 repairs the CUDA driver closure consumed by the proposal-gated
#3013 qualification. The host audit found a WSL dispatch chain with two
different ELF objects. The `ldd` dependency and the `/proc/<pid>/maps` driver
payload are related by the WSL driver architecture; they are not aliases of
one file.

## Host topology observed on 2026-09-27

All paths below were inspected read-only. The WSL `lib` mount is an overlay;
the Windows NVIDIA package is exposed by a read-only 9p mount at
`/usr/lib/wsl/drivers`.

| Path | lstat/stat | Size | SHA256 | Relation |
| --- | --- | ---: | --- | --- |
| `/usr/lib/wsl/lib/libcuda.so` | regular, mode `0o100555`, device `44`, inode `5348024557713090`, nlink `4` | 175,360 | `03a829ea8da94688327685c726b80ad64305ed4ed579b3092e8ee4bc17252ebd` | Same object as the next two paths; not a symlink |
| `/usr/lib/wsl/lib/libcuda.so.1` | regular, mode `0o100555`, device `44`, inode `5348024557713090`, nlink `4` | 175,360 | `03a829ea8da94688327685c726b80ad64305ed4ed579b3092e8ee4bc17252ebd` | Same object as the other two WSL `lib` paths; `ldd` resolves here |
| `/usr/lib/wsl/lib/libcuda.so.1.1` | regular, mode `0o100555`, device `44`, inode `5348024557713090`, nlink `4` | 175,360 | `03a829ea8da94688327685c726b80ad64305ed4ed579b3092e8ee4bc17252ebd` | Same object as the other two WSL `lib` paths; not the mapped driver payload |
| `/usr/lib/wsl/drivers/nvmdi.inf_amd64_47a93ea256b1ab85/libcuda_loader.so` | regular, mode `0o100555`, device `36`, inode `5348024557713090`, nlink `4` | 175,360 | `03a829ea8da94688327685c726b80ad64305ed4ed579b3092e8ee4bc17252ebd` | Identical bytes to the shim, but a different mounted object because its device differs |
| `/usr/lib/wsl/drivers/nvmdi.inf_amd64_47a93ea256b1ab85/nvmdi.inf` | regular, mode `0o100555`, device `36`, inode `7036874417978311`, nlink `1` | 313,790 | `5dd20d066e2c64897ee94064c600f9ed4d278c6be09c17d59e387ce5632f8442` | Package metadata; records driver date/version and is sealed with the payload |
| `/usr/lib/wsl/drivers/nvmdi.inf_amd64_47a93ea256b1ab85/libcuda.so.1.1` | regular, mode `0o100555`, device `36`, inode `6755399441257569`, nlink `1` | 25,874,608 | `dda4d950a8cbaa7d3c490e5684636547f2b502c6763a46bd652b8e3c8783e188` | Distinct object and distinct bytes; ELF SONAME is `libcuda.so.1`; this was the path in attempt A's process maps |

For every row, `lstat` and `stat` reported the same regular-file type, mode,
device, inode, and size. Every path had `readlink = none` and `realpath` equal
to its lexical path. The three `/usr/lib/wsl/lib` names share device and inode on the same
overlay mount, so they are hard-link names for one regular file object. The
driver-package loader has the same byte digest and inode number, but a
different device and a different mount; the identity contract treats it as a
byte-identical copy, not as the same file object. The large `libcuda.so.1.1`
payload has a different device/inode and different bytes from the shim.

The package-local `nvmdi.inf` at
`/usr/lib/wsl/drivers/nvmdi.inf_amd64_47a93ea256b1ab85/nvmdi.inf` reports
`DriverVer=12/02/2025, 32.0.15.9144`. The failed #3013 attempt A independently recorded the mapped
path above during its single server/model-load attempt, before any model-facing POST. NVIDIA's
[CUDA on WSL guide](https://docs.nvidia.com/cuda/wsl-user-guide/) describes
the Windows-host CUDA driver as stubbed into WSL. Together, the package mount,
matching `libcuda_loader.so`, the payload's SONAME, and attempt A's process-map
observation establish the narrow relation: the `/usr/lib/wsl/lib` object is
the guest-facing shim, while the separate NVIDIA package object is the mapped
driver payload behind it. They must not be collapsed into one object identity.

## Sealed identity contract

Candidate runtime manifest format 2 records a deterministic
`build.wsl_cuda_driver_closure` only when `ldd` resolves the logical
`libcuda.so.1` dependency to the recognized WSL shim. Preparation requires:

- the exact WSL `lib` and `drivers` mountpoints and observed filesystem roles;
- the known WSL shim names to identify one regular file object;
- exactly one `libcuda.so.1.1` payload in the read-only NVIDIA package layout;
- the package's `libcuda_loader.so` to match the shim bytes while retaining
  its distinct path and object identity as package evidence;
- an NVIDIA `nvmdi.inf` driver version and payload ELF SONAME `libcuda.so.1`.

For each accepted mapped object, the manifest seals its exact path, canonical
path, device, inode, mode, size, link count, ctime, mtime, and SHA256. Runtime
acceptance requires the `/proc/<pid>/maps` path to be in that exact set, the
map's major/minor device and inode to match the sealed stat identity, the live
file identity to remain unchanged, and the digest to match. Runtime hashes
the mapped files again at each attestation and requires the process map set to
remain stable after the first attestation. The separate driver payload is a
member of this explicit WSL contract; basename and hash alone never authorize
a path. The package's `libcuda_loader.so` copy helps prove the package
relationship, but is not accepted as a mapped runtime path because attempt A
observed the package's `libcuda.so.1.1` payload instead.

All other libraries keep exact-path identity. The special object set is
constructed only from the WSL `libcuda.so.1` dependency and its single,
validated NVIDIA package. An arbitrary `libcuda.so*` under `/tmp` or another
driver package is not in the set. No generic alias rule applies to
`libggml`, `libllama`, `libcublas`, or the CUDA toolkit runtime.

The existing process executable, argv, environment, CUDA toolkit, candidate
binary, candidate libraries, fresh `v1` head, and exact #3013 authority-comment
checks remain in force before every model-facing POST. Product cache stays
disabled; checkpointing stays enabled; `--swa-full` remains absent. This repair
does not authorize a physical run and does not revive attempt A.
