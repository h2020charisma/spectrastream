import ramanchada2 as rc2

import ramanchada2.spectrum as spectrum
import ramanchada2.spectrum.creators as ramanchada2


filename = "./src/experiments/NeonSNQ043_iR532_Probe_5msx2.txt"

spe = rc2.spectrum.from_local_file(
    filename,
    filetype=None,
)
