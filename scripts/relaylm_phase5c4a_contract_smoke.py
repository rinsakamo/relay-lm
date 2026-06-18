from phase5c4a_backend_e2e import main as backend_main
from relaylm_phase5c4a_renderer_smoke import main as renderer_main
from relaylm_phase5c4a_source_smoke import main as source_main

renderer_main()
source_main()
raise SystemExit(backend_main())
