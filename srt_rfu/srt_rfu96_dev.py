from srt_rfu.srt_rfu16_dev import SrtRfu16Dev


class SrtRfu16_11(SrtRfu16Dev):
    def __init__(self, exp_path, dye_exempt=None):
        super().__init__(exp_path, dye_exempt=dye_exempt)


class SrtRfu16_12(SrtRfu16Dev):
    def __init__(self, exp_path, dye_exempt=None):
        super().__init__(exp_path, dye_exempt=dye_exempt)


class SrtRfu16_21(SrtRfu16Dev):
    def __init__(self, exp_path, dye_exempt=None):
        super().__init__(exp_path, dye_exempt=dye_exempt)


class SrtRfu16_22(SrtRfu16Dev):
    def __init__(self, exp_path, dye_exempt=None):
        super().__init__(exp_path, dye_exempt=dye_exempt)


class SrtRfu16_31(SrtRfu16Dev):
    def __init__(self, exp_path, dye_exempt=None):
        super().__init__(exp_path, dye_exempt=dye_exempt)


class SrtRfu16_32(SrtRfu16Dev):
    def __init__(self, exp_path, dye_exempt=None):
        super().__init__(exp_path, dye_exempt=dye_exempt)


class SrtRfu96Dev:
    def __init__(self, exp_path, dye_exempt=None):
        self.blck11 = SrtRfu16_11(exp_path, dye_exempt)
        self.blck12 = SrtRfu16_12(exp_path, dye_exempt)
        self.blck21 = SrtRfu16_21(exp_path, dye_exempt)
        self.blck22 = SrtRfu16_22(exp_path, dye_exempt)
        self.blck31 = SrtRfu16_31(exp_path, dye_exempt)
        self.blck32 = SrtRfu16_32(exp_path, dye_exempt)
