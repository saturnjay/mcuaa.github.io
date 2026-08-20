"""Material 3 HCT color engine - Python port of material-color-utilities.

Reference: https://github.com/material-foundation/material-color-utilities
License: Apache 2.0, Copyright 2021 Google LLC
"""
import math


# --------------------------------------------------------------------------
# Color utils
# --------------------------------------------------------------------------

SRGB_TO_XYZ = [
    [0.41233895, 0.35762064, 0.18051042],
    [0.2126, 0.7152, 0.0722],
    [0.01932141, 0.11916382, 0.95034478],
]

XYZ_TO_SRGB = [
    [3.2413774792388685, -1.5376652402851851, -0.49885366846268053],
    [-0.9691452513005321, 1.8758853451067872, 0.04156585616912061],
    [0.05562093689691305, -0.20395524564742123, 1.0571799111220335],
]

WHITE_POINT_D65 = [95.047, 100.0, 108.883]


def argb_from_rgb(red, green, blue):
    return ((255 << 24) | ((red & 255) << 16) | ((green & 255) << 8) | (blue & 255))


def red_from_argb(argb):
    return (argb >> 16) & 255


def green_from_argb(argb):
    return (argb >> 8) & 255


def blue_from_argb(argb):
    return argb & 255


def hex_from_argb(argb):
    return "#{:06x}".format(argb & 0xFFFFFF)


def argb_from_hex(h):
    h = h.lstrip("#")
    return int(h, 16) | (255 << 24)


def linearized(rgb_component):
    normalized = rgb_component / 255.0
    if normalized <= 0.040449936:
        return normalized / 12.92 * 100.0
    return ((normalized + 0.055) / 1.055) ** 2.4 * 100.0


def delinearized(rgb_component):
    normalized = rgb_component / 100.0
    if normalized <= 0.0031308:
        d = normalized * 12.92
    else:
        d = 1.055 * (normalized ** (1.0 / 2.4)) - 0.055
    return max(0, min(255, round(d * 255.0)))


def argb_from_linrgb(linrgb):
    return argb_from_rgb(delinearized(linrgb[0]), delinearized(linrgb[1]), delinearized(linrgb[2]))


def argb_from_xyz(x, y, z):
    m = XYZ_TO_SRGB
    return argb_from_linrgb([
        m[0][0] * x + m[0][1] * y + m[0][2] * z,
        m[1][0] * x + m[1][1] * y + m[1][2] * z,
        m[2][0] * x + m[2][1] * y + m[2][2] * z,
    ])


def xyz_from_argb(argb):
    r = linearized(red_from_argb(argb))
    g = linearized(green_from_argb(argb))
    b = linearized(blue_from_argb(argb))
    m = SRGB_TO_XYZ
    return [
        m[0][0] * r + m[0][1] * g + m[0][2] * b,
        m[1][0] * r + m[1][1] * g + m[1][2] * b,
        m[2][0] * r + m[2][1] * g + m[2][2] * b,
    ]


def lab_f(t):
    e = 216.0 / 24389.0
    kappa = 24389.0 / 27.0
    if t > e:
        return t ** (1.0 / 3.0)
    return (kappa * t + 16) / 116


def lab_invf(ft):
    e = 216.0 / 24389.0
    kappa = 24389.0 / 27.0
    ft3 = ft * ft * ft
    if ft3 > e:
        return ft3
    return (116 * ft - 16) / kappa


def y_from_lstar(lstar):
    return 100.0 * lab_invf((lstar + 16.0) / 116.0)


def lstar_from_argb(argb):
    return lab_f(xyz_from_argb(argb)[1] / 100.0) * 116.0 - 16.0


def argb_from_lstar(lstar):
    c = delinearized(y_from_lstar(lstar))
    return argb_from_rgb(c, c, c)


def sanitize_degrees(degrees):
    degrees = degrees % 360.0
    if degrees < 0:
        degrees += 360.0
    return degrees


def signum(x):
    if x < 0:
        return -1.0
    if x > 0:
        return 1.0
    return 0.0


def matrix_multiply(row, matrix):
    """Matches TS mathUtils.matrixMultiply(row, matrix):
    result[i] = row[0]*matrix[i][0] + row[1]*matrix[i][1] + row[2]*matrix[i][2]
    """
    n = len(matrix)
    result = []
    for i in range(n):
        s = 0.0
        for k in range(len(row)):
            s += row[k] * matrix[i][k]
        result.append(s)
    return result


# --------------------------------------------------------------------------
# Viewing conditions (sRGB-like, DEFAULT)
# --------------------------------------------------------------------------

def _make_viewing_conditions():
    white = WHITE_POINT_D65
    adapting_luminance = (200.0 / math.pi) * y_from_lstar(50.0) / 100.0
    background_lstar = 50.0
    surround = 2.0
    discounting_illuminant = False

    xyz = white
    r_w = xyz[0] * 0.401288 + xyz[1] * 0.650173 + xyz[2] * -0.051461
    g_w = xyz[0] * -0.250268 + xyz[1] * 1.204414 + xyz[2] * 0.045854
    b_w = xyz[0] * -0.002079 + xyz[1] * 0.048952 + xyz[2] * 0.953127

    f = 0.8 + surround / 10.0
    if f >= 0.9:
        c = 0.59 + (0.69 - 0.59) * (f - 0.9) * 10.0
    else:
        c = 0.525 + (0.59 - 0.525) * (f - 0.8) * 10.0
    if discounting_illuminant:
        d = 1.0
    else:
        d = f * (1.0 - (1.0 / 3.6) * math.exp((-adapting_luminance - 42.0) / 92.0))
    d = max(0.0, min(1.0, d))

    nc = f
    rgb_d = [
        d * (100.0 / r_w) + 1.0 - d,
        d * (100.0 / g_w) + 1.0 - d,
        d * (100.0 / b_w) + 1.0 - d,
    ]
    k = 1.0 / (5.0 * adapting_luminance + 1.0)
    k4 = k ** 4
    k4_f = 1.0 - k4
    fl = k4 * adapting_luminance + 0.1 * k4_f * k4_f * (5.0 * adapting_luminance) ** (1.0 / 3.0)
    n = y_from_lstar(background_lstar) / white[1]
    z = 1.48 + math.sqrt(n)
    nbb = 0.725 / (n ** 0.2)
    ncb = nbb
    rgb_af = [
        ((fl * rgb_d[0] * r_w) / 100.0) ** 0.42,
        ((fl * rgb_d[1] * g_w) / 100.0) ** 0.42,
        ((fl * rgb_d[2] * b_w) / 100.0) ** 0.42,
    ]
    rgb_a = [
        (400.0 * rgb_af[0]) / (rgb_af[0] + 27.13),
        (400.0 * rgb_af[1]) / (rgb_af[1] + 27.13),
        (400.0 * rgb_af[2]) / (rgb_af[2] + 27.13),
    ]
    aw = (2.0 * rgb_a[0] + rgb_a[1] + 0.05 * rgb_a[2]) * nbb
    return {
        "n": n, "aw": aw, "nbb": nbb, "ncb": ncb, "c": c, "nc": nc,
        "rgb_d": rgb_d, "fl": fl, "f_l_root": fl ** 0.25, "z": z,
    }


VC = _make_viewing_conditions()


# --------------------------------------------------------------------------
# CAM16
# --------------------------------------------------------------------------

class Cam16:
    def __init__(self, hue, chroma, j, q, m, s, jstar, astar, bstar):
        self.hue = hue
        self.chroma = chroma
        self.j = j
        self.q = q
        self.m = m
        self.s = s
        self.jstar = jstar
        self.astar = astar
        self.bstar = bstar

    @staticmethod
    def from_int(argb):
        red = (argb & 0x00FF0000) >> 16
        green = (argb & 0x0000FF00) >> 8
        blue = argb & 0x000000FF
        red_l = linearized(red)
        green_l = linearized(green)
        blue_l = linearized(blue)
        x = 0.41233895 * red_l + 0.35762064 * green_l + 0.18051042 * blue_l
        y = 0.2126 * red_l + 0.7152 * green_l + 0.0722 * blue_l
        z = 0.01932141 * red_l + 0.11916382 * green_l + 0.95034478 * blue_l

        r_c = 0.401288 * x + 0.650173 * y - 0.051461 * z
        g_c = -0.250268 * x + 1.204414 * y + 0.045854 * z
        b_c = -0.002079 * x + 0.048952 * y + 0.953127 * z

        r_d = VC["rgb_d"][0] * r_c
        g_d = VC["rgb_d"][1] * g_c
        b_d = VC["rgb_d"][2] * b_c

        r_af = (VC["fl"] * abs(r_d) / 100.0) ** 0.42
        g_af = (VC["fl"] * abs(g_d) / 100.0) ** 0.42
        b_af = (VC["fl"] * abs(b_d) / 100.0) ** 0.42

        r_a = signum(r_d) * 400.0 * r_af / (r_af + 27.13)
        g_a = signum(g_d) * 400.0 * g_af / (g_af + 27.13)
        b_a = signum(b_d) * 400.0 * b_af / (b_af + 27.13)

        a = (11.0 * r_a + -12.0 * g_a + b_a) / 11.0
        b = (r_a + g_a - 2.0 * b_a) / 9.0
        u = (20.0 * r_a + 20.0 * g_a + 21.0 * b_a) / 20.0
        p2 = (40.0 * r_a + 20.0 * g_a + b_a) / 20.0
        hue = sanitize_degrees(math.degrees(math.atan2(b, a)))
        hue_rad = math.radians(hue)

        ac = p2 * VC["nbb"]
        j = 100.0 * (ac / VC["aw"]) ** (VC["c"] * VC["z"])
        q = (4.0 / VC["c"]) * math.sqrt(j / 100.0) * (VC["aw"] + 4.0) * VC["f_l_root"]
        hue_prime = hue + 360 if hue < 20.14 else hue
        e_hue = 0.25 * (math.cos(math.radians(hue_prime) + 2.0) + 3.8)
        p1 = (50000.0 / 13.0) * e_hue * VC["nc"] * VC["ncb"]
        t = (p1 * math.sqrt(a * a + b * b)) / (u + 0.305)
        alpha = (t ** 0.9) * (1.64 - 0.29 ** VC["n"]) ** 0.73
        c = alpha * math.sqrt(j / 100.0)
        m = c * VC["f_l_root"]
        s = 50.0 * math.sqrt((alpha * VC["c"]) / (VC["aw"] + 4.0))
        jstar = ((1.0 + 100.0 * 0.007) * j) / (1.0 + 0.007 * j)
        mstar = (1.0 / 0.0228) * math.log(1.0 + 0.0228 * m)
        astar = mstar * math.cos(hue_rad)
        bstar = mstar * math.sin(hue_rad)
        return Cam16(hue, c, j, q, m, s, jstar, astar, bstar)

    def viewed(self):
        alpha = 0.0 if (self.chroma == 0.0 or self.j == 0.0) else self.chroma / math.sqrt(self.j / 100.0)
        t = (alpha / (1.64 - 0.29 ** VC["n"]) ** 0.73) ** (1.0 / 0.9)
        h_rad = math.radians(self.hue)
        e_hue = 0.25 * (math.cos(h_rad + 2.0) + 3.8)
        ac = VC["aw"] * (self.j / 100.0) ** (1.0 / VC["c"] / VC["z"])
        p1 = e_hue * (50000.0 / 13.0) * VC["nc"] * VC["ncb"]
        p2 = ac / VC["nbb"]
        h_sin = math.sin(h_rad)
        h_cos = math.cos(h_rad)
        gamma = (23.0 * (p2 + 0.305) * t) / (23.0 * p1 + 11.0 * t * h_cos + 108.0 * t * h_sin)
        a = gamma * h_cos
        b = gamma * h_sin
        r_a = (460.0 * p2 + 451.0 * a + 288.0 * b) / 1403.0
        g_a = (460.0 * p2 - 891.0 * a - 261.0 * b) / 1403.0
        b_a = (460.0 * p2 - 220.0 * a - 6300.0 * b) / 1403.0
        r_c_base = max(0, (27.13 * abs(r_a)) / (400.0 - abs(r_a)))
        r_c = signum(r_a) * (100.0 / VC["fl"]) * r_c_base ** (1.0 / 0.42)
        g_c_base = max(0, (27.13 * abs(g_a)) / (400.0 - abs(g_a)))
        g_c = signum(g_a) * (100.0 / VC["fl"]) * g_c_base ** (1.0 / 0.42)
        b_c_base = max(0, (27.13 * abs(b_a)) / (400.0 - abs(b_a)))
        b_c = signum(b_a) * (100.0 / VC["fl"]) * b_c_base ** (1.0 / 0.42)
        r_f = r_c / VC["rgb_d"][0]
        g_f = g_c / VC["rgb_d"][1]
        b_f = b_c / VC["rgb_d"][2]
        x = 1.86206786 * r_f - 1.01125463 * g_f + 0.14918677 * b_f
        y = 0.38752654 * r_f + 0.62144744 * g_f - 0.00897398 * b_f
        z = -0.01584150 * r_f - 0.03412294 * g_f + 1.04996444 * b_f
        return argb_from_xyz(x, y, z)


# --------------------------------------------------------------------------
# HCT solver
# --------------------------------------------------------------------------

SCALED_DISCOUNT_FROM_LINRGB = [
    [0.001200833568784504, 0.002389694492170889, 0.0002795742885861124],
    [0.0005891086651375999, 0.0029785502573438758, 0.0003270666104008398],
    [0.00010146692491640572, 0.0005364214359186694, 0.0032979401770712076],
]

LINRGB_FROM_SCALED_DISCOUNT = [
    [1373.2198709594231, -1100.4251190754821, -7.278681089101213],
    [-271.815969077903, 559.6580465940733, -32.46047482791194],
    [1.9622899599665666, -57.173814538844006, 308.7233197812385],
]

Y_FROM_LINRGB = [0.2126, 0.7152, 0.0722]

CRITICAL_PLANES = [
    0.015176349177441876, 0.045529047532325624, 0.07588174588720938,
    0.10623444424209313, 0.13658714259697685, 0.16693984095186062,
    0.19729253930674434, 0.2276452376616281, 0.2579979360165119,
    0.28835063437139563, 0.3188300904430532, 0.350925934958123,
    0.3848314933096426, 0.42057480301049466, 0.458183274052838,
    0.4976837250274023, 0.5391024159806381, 0.5824650784040898,
    0.6277969426914107, 0.6751227633498623, 0.7244668422128921,
    0.775853049866786, 0.829304845476233, 0.8848452951698498,
    0.942497089126609, 1.0022825574869039, 1.0642236851973577,
    1.1283421258858297, 1.1946592148522128, 1.2631959812511864,
    1.3339731595349034, 1.407011200216447, 1.4823302800086415,
    1.5599503113873272, 1.6398909516233677, 1.7221716113234105,
    1.8068114625156377, 1.8938294463134073, 1.9832442801866852,
    2.075074464868551, 2.1693382909216234, 2.2660538449872063,
    2.36523901573795, 2.4669114995532007, 2.5710888059345764,
    2.6777882626779785, 2.7870270208169257, 2.898822059350997,
    3.0131901897720907, 3.1301480604002863, 3.2497121605402226,
    3.3718988244681087, 3.4967242352587946, 3.624204428461639,
    3.754355295633311, 3.887192587735158, 4.022731918402185,
    4.160988767090289, 4.301978482107941, 4.445716283538092,
    4.592217266055746, 4.741496401646282, 4.893568542229298,
    5.048448422192488, 5.20615066083972, 5.3666897647573375,
    5.5300801301023865, 5.696336044816294, 5.865471690767354,
    6.037501145825082, 6.212438385869475, 6.390297286737924,
    6.571091626112461, 6.7548350853498045, 6.941541251256611,
    7.131223617812143, 7.323895587840543, 7.5195704746346665,
    7.7182615035334345, 7.919981813454504, 8.124744458384042,
    8.332562408825165, 8.543448553206703, 8.757415699253682,
    8.974476575321063, 9.194643831691977, 9.417930041841839,
    9.644347703669503, 9.873909240696694, 10.106627003236781,
    10.342513269534024, 10.58158024687427, 10.8238400726681,
    11.069304815507364, 11.317986476196008, 11.569896988756009,
    11.825048221409341, 12.083451977536606, 12.345119996613247,
    12.610063955123938, 12.878295467455942, 13.149826086772048,
    13.42466730586372, 13.702830557985108, 13.984327217668513,
    14.269168601521828, 14.55736596900856, 14.848930523210871,
    15.143873411576273, 15.44220572664832, 15.743938506781891,
    16.04908273684337, 16.35764934889634, 16.66964922287304,
    16.985093187232053, 17.30399201960269, 17.62635644741625,
    17.95219714852476, 18.281524751807332, 18.614349837764564,
    18.95068293910138, 19.290534541298456, 19.633915083172692,
    19.98083495742689, 20.331304511189067, 20.685334046541502,
    21.042933821039977, 21.404114048223256, 21.76888489811322,
    22.137256497705877, 22.50923893145328, 22.884842241736916,
    23.264076429332462, 23.6469514538663, 24.033477234264016,
    24.42366364919083, 24.817520537484558, 25.21505769858089,
    25.61628489293138, 26.021211842414342, 26.429848230738664,
    26.842203703840827, 27.258287870275353, 27.678110301598522,
    28.10168053274597, 28.529008062403893, 28.96010235337422,
    29.39497283293396, 29.83362889318845, 30.276079891419332,
    30.722335150426627, 31.172403958865512, 31.62629557157785,
    32.08401920991837, 32.54558406207592, 33.010999283389665,
    33.4802739966603, 33.953417292456834, 34.430438229418264,
    34.911345834551085, 35.39614910352207, 35.88485700094671,
    36.37747846067349, 36.87402238606382, 37.37449765026789,
    37.87891309649659, 38.38727753828926, 38.89959975977785,
    39.41588851594697, 39.93615253289054, 40.460400508064545,
    40.98864111053629, 41.520882981230194, 42.05713473317016,
    42.597404951718396, 43.141702194811224, 43.6900349931913,
    44.24241185063697, 44.798841244188324, 45.35933162437017,
    45.92389141541209, 46.49252901546552, 47.065252796817916,
    47.64207110610409, 48.22299226451468, 48.808024568002054,
    49.3971762874833, 49.9904556690408, 50.587870934119984,
    51.189430279724725, 51.79514187861014, 52.40501387947288,
    53.0190544071392, 53.637271562750364, 54.259673423945976,
    54.88626804504493, 55.517063457223934, 56.15206766869424,
    56.79128866487574, 57.43473440856916, 58.08241284012621,
    58.734331877617365, 59.39049941699807, 60.05092333227251,
    60.715611475655585, 61.38457167773311, 62.057811747619894,
    62.7353394731159, 63.417162620860914, 64.10328893648692,
    64.79372614476921, 65.48848194977529, 66.18756403501224,
    66.89098006357258, 67.59873767827808, 68.31084450182222,
    69.02730813691093, 69.74813616640164, 70.47333615344107,
    71.20291564160104, 71.93688215501312, 72.67524319850172,
    73.41800625771542, 74.16517879925733, 74.9167682708136,
    75.67278210128072, 76.43322770089146, 77.1981124613393,
    77.96744375590167, 78.74122893956174, 79.51947534912904,
    80.30219030335869, 81.08938110306934, 81.88105503125999,
    82.67721935322541, 83.4778813166706, 84.28304815182372,
    85.09272707154808, 85.90692527145302, 86.72564993000343,
    87.54890820862819, 88.3767072518277, 89.2090541872801,
    90.04595612594655, 90.88742016217518, 91.73345337380438,
    92.58406282226491, 93.43925555268066, 94.29903859396902,
    95.16341895893969, 96.03240364439274, 96.9059996312159,
    97.78421388448044, 98.6670533535366, 99.55452497210776,
]


def _sanitize_radians(angle):
    return (angle + math.pi * 8) % (math.pi * 2)


def _true_delinearized(rgb_component):
    normalized = rgb_component / 100.0
    if normalized <= 0.0031308:
        d = normalized * 12.92
    else:
        d = 1.055 * (normalized ** (1.0 / 2.4)) - 0.055
    return d * 255.0


def _chromatic_adaptation(component):
    af = abs(component) ** 0.42
    return signum(component) * 400.0 * af / (af + 27.13)


def _hue_of(linrgb):
    scaled = matrix_multiply(linrgb, SCALED_DISCOUNT_FROM_LINRGB)
    r_a = _chromatic_adaptation(scaled[0])
    g_a = _chromatic_adaptation(scaled[1])
    b_a = _chromatic_adaptation(scaled[2])
    a = (11.0 * r_a + -12.0 * g_a + b_a) / 11.0
    b = (r_a + g_a - 2.0 * b_a) / 9.0
    return math.atan2(b, a)


def _are_in_cyclic_order(a, b, c):
    return _sanitize_radians(b - a) < _sanitize_radians(c - a)


def _intercept(source, mid, target):
    return (mid - source) / (target - source)


def _lerp_point(source, t, target):
    return [
        source[0] + (target[0] - source[0]) * t,
        source[1] + (target[1] - source[1]) * t,
        source[2] + (target[2] - source[2]) * t,
    ]


def _set_coordinate(source, coordinate, target, axis):
    return _lerp_point(source, _intercept(source[axis], coordinate, target[axis]), target)


def _is_bounded(x):
    return 0.0 <= x <= 100.0


def _nth_vertex(y, n):
    k_r, k_g, k_b = Y_FROM_LINRGB
    coord_a = 0.0 if n % 4 <= 1 else 100.0
    coord_b = 0.0 if n % 2 == 0 else 100.0
    if n < 4:
        g, b = coord_a, coord_b
        r = (y - g * k_g - b * k_b) / k_r
    elif n < 8:
        b, r = coord_a, coord_b
        g = (y - r * k_r - b * k_b) / k_g
    else:
        r, g = coord_a, coord_b
        b = (y - r * k_r - g * k_g) / k_b
    if _is_bounded(r) and _is_bounded(g) and _is_bounded(b):
        return [r, g, b]
    return [-1.0, -1.0, -1.0]


def _bisect_to_segment(y, target_hue):
    left = right = [-1.0, -1.0, -1.0]
    left_hue = right_hue = 0.0
    initialized = False
    uncut = True
    for n in range(12):
        mid = _nth_vertex(y, n)
        if mid[0] < 0:
            continue
        mid_hue = _hue_of(mid)
        if not initialized:
            left = right = mid
            left_hue = right_hue = mid_hue
            initialized = True
            continue
        if uncut or _are_in_cyclic_order(left_hue, mid_hue, right_hue):
            uncut = False
            if _are_in_cyclic_order(left_hue, target_hue, mid_hue):
                right, right_hue = mid, mid_hue
            else:
                left, left_hue = mid, mid_hue
    return [left, right]


def _midpoint(a, b):
    return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2]


def _critical_plane_below(x):
    return math.floor(x - 0.5)


def _critical_plane_above(x):
    return math.ceil(x - 0.5)


def _bisect_to_limit(y, target_hue):
    segment = _bisect_to_segment(y, target_hue)
    left = list(segment[0])
    left_hue = _hue_of(left)
    right = list(segment[1])
    for axis in range(3):
        if left[axis] != right[axis]:
            if left[axis] < right[axis]:
                l_plane = _critical_plane_below(_true_delinearized(left[axis]))
                r_plane = _critical_plane_above(_true_delinearized(right[axis]))
            else:
                l_plane = _critical_plane_above(_true_delinearized(left[axis]))
                r_plane = _critical_plane_below(_true_delinearized(right[axis]))
            for _ in range(8):
                if abs(r_plane - l_plane) <= 1:
                    break
                m_plane = math.floor((l_plane + r_plane) / 2.0)
                mid = _set_coordinate(left, CRITICAL_PLANES[m_plane], right, axis)
                mid_hue = _hue_of(mid)
                if _are_in_cyclic_order(left_hue, target_hue, mid_hue):
                    right, r_plane = mid, m_plane
                else:
                    left, left_hue, l_plane = mid, mid_hue, m_plane
    return _midpoint(left, right)


def _inverse_chromatic_adaptation(adapted):
    adapted_abs = abs(adapted)
    base = max(0, 27.13 * adapted_abs / (400.0 - adapted_abs))
    return signum(adapted) * base ** (1.0 / 0.42)


def _find_result_by_j(hue_radians, chroma, y):
    j = math.sqrt(y) * 11.0
    t_inner_coeff = 1 / (1.64 - 0.29 ** VC["n"]) ** 0.73
    e_hue = 0.25 * (math.cos(hue_radians + 2.0) + 3.8)
    p1 = e_hue * (50000.0 / 13.0) * VC["nc"] * VC["ncb"]
    h_sin = math.sin(hue_radians)
    h_cos = math.cos(hue_radians)
    for iteration in range(5):
        j_normalized = j / 100.0
        alpha = 0.0 if (chroma == 0.0 or j == 0.0) else chroma / math.sqrt(j_normalized)
        t = (alpha * t_inner_coeff) ** (1.0 / 0.9)
        ac = VC["aw"] * (j_normalized ** (1.0 / VC["c"] / VC["z"]))
        p2 = ac / VC["nbb"]
        gamma = 23.0 * (p2 + 0.305) * t / (23.0 * p1 + 11 * t * h_cos + 108.0 * t * h_sin)
        a = gamma * h_cos
        b = gamma * h_sin
        r_a = (460.0 * p2 + 451.0 * a + 288.0 * b) / 1403.0
        g_a = (460.0 * p2 - 891.0 * a - 261.0 * b) / 1403.0
        b_a = (460.0 * p2 - 220.0 * a - 6300.0 * b) / 1403.0
        linrgb = matrix_multiply(
            [_inverse_chromatic_adaptation(r_a),
             _inverse_chromatic_adaptation(g_a),
             _inverse_chromatic_adaptation(b_a)],
            LINRGB_FROM_SCALED_DISCOUNT)
        if min(linrgb) < 0:
            return 0
        fnj = Y_FROM_LINRGB[0] * linrgb[0] + Y_FROM_LINRGB[1] * linrgb[1] + Y_FROM_LINRGB[2] * linrgb[2]
        if fnj <= 0:
            return 0
        if iteration == 4 or abs(fnj - y) < 0.002:
            if max(linrgb) > 100.01:
                return 0
            return argb_from_linrgb(linrgb)
        j = j - (fnj - y) * j / (2 * fnj)
    return 0


def solve_to_int(hue_degrees, chroma, lstar):
    if chroma < 0.0001 or lstar < 0.0001 or lstar > 99.9999:
        return argb_from_lstar(lstar)
    hue_degrees = sanitize_degrees(hue_degrees)
    hue_radians = math.radians(hue_degrees)
    y = y_from_lstar(lstar)
    exact = _find_result_by_j(hue_radians, chroma, y)
    if exact != 0:
        return exact
    linrgb = _bisect_to_limit(y, hue_radians)
    return argb_from_linrgb(linrgb)


class Hct:
    def __init__(self, hue, chroma, tone):
        self.hue = hue
        self.chroma = chroma
        self.tone = tone

    @classmethod
    def from_argb(cls, argb):
        cam = Cam16.from_int(argb)
        return cls(cam.hue, cam.chroma, lstar_from_argb(argb))

    def to_int(self):
        return solve_to_int(self.hue, self.chroma, self.tone)


class TonalPalette:
    def __init__(self, hue, chroma):
        self.hue = hue
        self.chroma = chroma
        self._cache = {}

    @classmethod
    def from_argb(cls, argb):
        hct = Hct.from_argb(argb)
        return cls(hct.hue, hct.chroma)

    def tone(self, tone):
        if tone not in self._cache:
            self._cache[tone] = solve_to_int(self.hue, self.chroma, tone)
        return self._cache[tone]


def scheme_light(seed_argb):
    primary = TonalPalette.from_argb(seed_argb)
    secondary = TonalPalette(primary.hue, max(8.0, min(primary.chroma * 0.5, 24.0)))
    tertiary = TonalPalette(primary.hue + 60.0, min(primary.chroma * 0.6, 32.0))
    neutral = TonalPalette(primary.hue, 4.0)
    neutral_variant = TonalPalette(primary.hue, 8.0)
    return {
        "primary": primary.tone(40), "on-primary": primary.tone(100),
        "primary-container": primary.tone(90), "on-primary-container": primary.tone(10),
        "inverse-primary": primary.tone(80), "on-inverse-primary": primary.tone(20),
        "secondary": secondary.tone(40), "on-secondary": secondary.tone(100),
        "secondary-container": secondary.tone(90), "on-secondary-container": secondary.tone(10),
        "tertiary": tertiary.tone(40), "on-tertiary": tertiary.tone(100),
        "tertiary-container": tertiary.tone(90), "on-tertiary-container": tertiary.tone(10),
        "error": 0xBA1A1A, "on-error": 0xFFFFFF,
        "error-container": 0xFFDAD6, "on-error-container": 0x410002,
        "background": neutral.tone(98), "on-background": neutral.tone(10),
        "surface": neutral.tone(98), "on-surface": neutral.tone(10),
        "surface-variant": neutral_variant.tone(90), "on-surface-variant": neutral_variant.tone(30),
        "inverse-surface": neutral.tone(20), "inverse-on-surface": neutral.tone(95),
        "outline": neutral_variant.tone(50), "outline-variant": neutral_variant.tone(80),
        "shadow": 0x000000, "scrim": 0x000000,
        "surface-dim": neutral.tone(87), "surface-bright": neutral.tone(98),
        "surface-container-lowest": neutral.tone(100), "surface-container-low": neutral.tone(96),
        "surface-container": neutral.tone(94), "surface-container-high": neutral.tone(92),
        "surface-container-highest": neutral.tone(90),
        "surface-tint": primary.tone(40),
    }


def scheme_dark(seed_argb):
    primary = TonalPalette.from_argb(seed_argb)
    secondary = TonalPalette(primary.hue, max(8.0, min(primary.chroma * 0.5, 24.0)))
    tertiary = TonalPalette(primary.hue + 60.0, min(primary.chroma * 0.6, 32.0))
    neutral = TonalPalette(primary.hue, 4.0)
    neutral_variant = TonalPalette(primary.hue, 8.0)
    return {
        "primary": primary.tone(80), "on-primary": primary.tone(20),
        "primary-container": primary.tone(30), "on-primary-container": primary.tone(90),
        "inverse-primary": primary.tone(40), "on-inverse-primary": primary.tone(100),
        "secondary": secondary.tone(80), "on-secondary": secondary.tone(20),
        "secondary-container": secondary.tone(30), "on-secondary-container": secondary.tone(90),
        "tertiary": tertiary.tone(80), "on-tertiary": tertiary.tone(20),
        "tertiary-container": tertiary.tone(30), "on-tertiary-container": tertiary.tone(90),
        "error": 0xFFB4AB, "on-error": 0x690005,
        "error-container": 0x93000A, "on-error-container": 0xFFDAD6,
        "background": neutral.tone(6), "on-background": neutral.tone(90),
        "surface": neutral.tone(6), "on-surface": neutral.tone(90),
        "surface-variant": neutral_variant.tone(30), "on-surface-variant": neutral_variant.tone(80),
        "inverse-surface": neutral.tone(90), "inverse-on-surface": neutral.tone(20),
        "outline": neutral_variant.tone(60), "outline-variant": neutral_variant.tone(30),
        "shadow": 0x000000, "scrim": 0x000000,
        "surface-dim": neutral.tone(6), "surface-bright": neutral.tone(24),
        "surface-container-lowest": neutral.tone(4), "surface-container-low": neutral.tone(10),
        "surface-container": neutral.tone(12), "surface-container-high": neutral.tone(17),
        "surface-container-highest": neutral.tone(22),
        "surface-tint": primary.tone(80),
    }


if __name__ == "__main__":
    seed = argb_from_hex("#4460A5")
    print("=== LIGHT ===")
    for k, v in scheme_light(seed).items():
        print("{:<28} {}".format(k, hex_from_argb(v)))
    print("=== DARK ===")
    for k, v in scheme_dark(seed).items():
        print("{:<28} {}".format(k, hex_from_argb(v)))
