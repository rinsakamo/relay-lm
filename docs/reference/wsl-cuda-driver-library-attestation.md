# WSL CUDA driver library identity attestation

The distinct [exploratory campaign design](wsl-cuda-exploratory-campaign.md)
defines bounded discovery before independent reproduction. Its offline maps
diagnostic is implemented; the campaign launcher remains deferred. Neither
the design nor diagnostic grants execution authority or changes strict closure
acceptance below. Consumed rehearsal E cannot be replayed.

Issue #3015 established the WSL CUDA guest-shim to NVIDIA package-payload
relationship for #3013. Issue #3018 extends that contract after attempt B
stopped at the first undeclared live mapping, `libnvdxgdmal.so.1`. The product
cache remains disabled; this apparatus change does not authorize a CUDA
qualification or a physical rehearsal.

## Attempt-B evidence boundary

The preserved attempt-B preflight, cold transaction, attempt summary, server
log, cleanup record, and evidence manifests were read in place. The cold
failure names this live path:

```text
/usr/lib/wsl/drivers/nvmdi.inf_amd64_47a93ea256b1ab85/libnvdxgdmal.so.1
```

No `/proc/746241/maps`, derived process-map list, executable/start-time
snapshot, or complete closure trace was preserved. The complete attempt-B
mapped-file set therefore cannot be recovered. The only NVIDIA package path
directly proven mapped at the failed gate is `libnvdxgdmal.so.1`. The
`libcuda.so.1.1` payload and `libcuda_loader.so` are in B's prepared closure
evidence, but their B map membership cannot be independently confirmed. Every
other package member has unknown B map membership; absence from the saved
evidence is not evidence that it was unmapped. No attempt was spent to
reconstruct the missing map.

### Preserved package identity and proven mappings

The preflight bound package directory
`/usr/lib/wsl/drivers/nvmdi.inf_amd64_47a93ea256b1ab85`, device 36, inode
7036874417978311, mode 33133, size 313790, link count 1, ctime_ns
1765707979487323400, mtime_ns 1764690947000000000, and SHA256
`5dd20d066e2c64897ee94064c600f9ed4d278c6be09c17d59e387ce5632f8442`. Its
`nvmdi.inf` records DriverVer `12/02/2025, 32.0.15.9144`.

| Role | Literal path | realpath | Device / inode | Mode / size / links | ctime_ns / mtime_ns | SHA256 | ELF SONAME / NEEDED | Attempt-B membership |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WSL guest shim aliases | `/usr/lib/wsl/lib/libcuda.so`, `.so.1`, `.so.1.1` | Same as each literal path | 44 / 5348024557713090 | 33133 / 175360 / 4 | 1765707995028388500 / 1764690947000000000 | `03a829ea8da94688327685c726b80ad64305ed4ed579b3092e8ee4bc17252ebd` | SONAME `libcuda.so.1`; same ELF identity for all aliases | Prepared closure evidence only; full map membership not preserved |
| Package payload | `/usr/lib/wsl/drivers/nvmdi.inf_amd64_47a93ea256b1ab85/libcuda.so.1.1` | Same as literal path | 36 / 6755399441257569 | 33133 / 25874608 / 1 | 1765707985838876900 / 1764690947000000000 | `dda4d950a8cbaa7d3c490e5684636547f2b502c6763a46bd652b8e3c8783e188` | `libcuda.so.1`; `libc.so.6`, `libm.so.6`, `libdl.so.2`, `libpthread.so.0`, `librt.so.1` | In B preflight closure; live mapping not independently recoverable |
| Required CUDA initialization companion | `/usr/lib/wsl/drivers/nvmdi.inf_amd64_47a93ea256b1ab85/libnvdxgdmal.so.1` | Same as literal path | 36 / 3377699720738305 | 33133 / 67576 / 1 | 1765707986239722500 / 1764690947000000000 | `d99311dd67f6fd05f5ee16515dcacaf2afef816580f10e19eb512353701b4741` | `libnvdxgdmal.so.1`; `libc.so.6`, `libdl.so.2`, `libpthread.so.0` | **Observed mapped:** the B live identity gate reported this exact undeclared path |
| Loader relationship evidence only | `/usr/lib/wsl/drivers/nvmdi.inf_amd64_47a93ea256b1ab85/libcuda_loader.so` | Same as literal path | 36 / 5348024557713090 | 33133 / 175360 / 4 | 1765707995028388500 / 1764690947000000000 | `03a829ea8da94688327685c726b80ad64305ed4ed579b3092e8ee4bc17252ebd` | SONAME `libcuda.so.1`; `libc.so.6`, `libdl.so.2`, `libpthread.so.0` | Membership not independently recoverable; not an accepted mapped path |

The shim and package loader have matching bytes and inode values on different
mounted devices, so they remain distinct file identities. `libcuda.so.1.1` is
also a distinct object and byte stream from the guest shim.

## Exact package static inspection

The exact package contains these 18 shared objects. Package presence alone
does not admit an object. Only the two role-bearing members in the preceding
table are accepted by the runtime contract.

| Package object | Static classification | Rationale and attempt-B evidence |
| --- | --- | --- |
| `libcuda.so.1.1` | Required mapped runtime payload | SONAME is `libcuda.so.1`; sealed by the existing #3015 preparation path. B's complete map is absent, so direct B membership is unknown. |
| `libnvdxgdmal.so.1` | Required mapped CUDA initialization companion | Exact path was observed at B's failed live identity gate. NVIDIA's [WSL2 CUDA runtime report](https://github.com/NVIDIA/nvidia-container-toolkit/issues/520) documents that Windows driver 555+ needs this object mapped for CUDA initialization. |
| `libcuda_loader.so` | Evidence-only package object | SONAME and bytes match the shim, but the distinct 9p object is not admitted as a process-map alias. |
| `libnvidia-gpucomp.so`, `libnvidia-nvvm.so.4`, `libnvidia-nvvm70.so.4`, `libnvidia-ptxjitcompiler.so.1`, `libnvidia-tileiras.so` | Unknown possible dynamic-load objects | Names occur in CUDA/JIT strings or related loader metadata, but the saved B map does not establish this model-load path. Fail closed. |
| `libnvdxdlkernels.so`, `libnvwgf2umx.so` | Unknown possible dynamic-load objects | No direct `DT_NEEDED` edge from the sealed payload or `libnvdxgdmal.so.1`; no B map evidence. Fail closed. |
| `libcudadebugger.so.1` | Unrelated debugger subgraph | Debugger support; no edge from the sealed CUDA payload's `DT_NEEDED` list. |
| `libnvcuvid.so.1` | Unrelated video decode subgraph | Its direct `DT_NEEDED` includes `libdxcore.so`; the video path is not the CUDA compute initialization path used here. |
| `libnvidia-encode.so.1`, `libnvidia-opticalflow.so.1` | Unrelated video subgraph | Both have a direct dependency on `libnvcuvid.so.1`; not reached by the sealed compute payload's direct ELF dependencies. |
| `libnvidia-ml.so.1`, `libnvidia-ml_loader.so` | Unrelated management subgraph | NVML names are not direct dependencies of the sealed compute payload. |
| `libnvidia-ngx.so.1`, `libnvoptix_loader.so.1` | Unrelated graphics/NGX subgraphs | No direct dependency from the sealed compute payload or its observed companion. |

The package `libcuda.so.1.1` and `libnvdxgdmal.so.1` each have only ordinary
system libraries in their direct `DT_NEEDED` entries. There is no direct ELF
dependency from one to the other. The companion is admitted based on the
attempt-B live gate observation and WSL CUDA runtime evidence, not because its
filename appears in the package. The `libdxcore.so` string in package objects
is not itself evidence that this model-load path mapped it. Its only direct
package `DT_NEEDED` edge in this inventory is from the unrelated
`libnvcuvid.so.1` video path. No other possible dynamic object is admitted
without a separate owner-authorized evidence update.

## Contract v2

The candidate manifest records
`build.wsl_cuda_driver_closure` with schema version 2 and contract
`wsl-nvidia-cuda-runtime-package-closure-v2`. It binds:

- logical dependency `libcuda.so.1` to the exact WSL guest shim path, aliases,
  mount identity, file identity, SHA256, ELF SONAME, and `DT_NEEDED` list;
- the read-only 9p `drivers` mount and one exact
  `nvmdi.inf_amd64_<identity>` directory, including directory identity and
  INF path, identity, digest, date, driver version, and declarations for the
  payload, loader copy, and runtime companion;
- the package loader copy as relationship evidence only; and
- exactly two package runtime objects, each with literal and real paths,
  device/inode, mode, size, link count, ctime/mtime, SHA256, SONAME,
  `DT_NEEDED`, role, package name, and evidence relationship.

The package object set is fixed in code to `libcuda.so.1.1` and
`libnvdxgdmal.so.1`; collection does not glob package `.so` files. A different
INF revision, package directory, path, device/inode, metadata, SHA, ELF
identity, role, or relationship fails closed. An unknown `.so` in the same
directory, the same basename in another package, or identical bytes at
`/tmp` or elsewhere under `/usr/lib/wsl/drivers` is not admitted.

At each live closure attestation, runtime verifies the sealed shim, package
directory, INF, loader relationship, and both role-bearing package objects.
Every mapped library must then be either an exact ordinary path in the sealed
candidate `ldd` closure or an exact path in the explicit WSL accepted-object
set. The map's major/minor device and inode, live direct regular-file identity,
sealed full identity, and SHA256 must match. The #3013 caller retains its
before-every-model-facing-POST re-attestation and stable-map checks. Ordinary
non-WSL closures keep their exact-path behavior.

The package set is fail-closed: evidence-only, unrelated, and unknown objects
are never silently promoted into the accepted mapping set. The contract does
not accept a package wildcard, basename match, hash match at any path, or
whatever `/proc/maps` happens to report.

## Zero-request rehearsal boundary

The registered #3018 target is
`diagnostic:3018-wsl-nvidia-runtime-closure-rehearsal`, with a distinct
apparatus attempt identity. Its proposal freezes the exact candidate manifest,
server/model/runtime digests, descriptor, receipt, preflight and output paths,
port 1234, argv, one server launch, one model load, and zero model-facing
POSTs, generation requests, input-count requests, or public completions. It
waits for the same model-loaded server state, captures the complete
`/proc/<pid>/maps` snapshot twice, attests the mapped library closure, and
terminates the owned process. Its code makes no HTTP call, checks that the
server log contains no POST, does not invoke RelayLM, and does not exercise
cache correctness.

The descriptor marker `PROPOSAL_ONLY_NOT_EXECUTION_AUTHORITY` cannot authorize
execution. A later exact #3018 owner comment must bind the descriptor digest,
candidate, model, closure, target, attempt, and zero-request ceilings; the
canonical physical queue remains mandatory. Preparing the descriptor is
separate from execution. This contract repair does not create #3013 attempt C
or grant authority for any rehearsal.
