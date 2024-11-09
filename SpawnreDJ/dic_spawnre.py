# dic_spawnre.py

genre_mapping = {
    'A00': {
        'Hex': '0x00',
        'Genre': 'rock',
        'Parent': None,
        'Related': []
    },
    'A01': {
        'Hex': '0x01',
        'Genre': 'classic rock',
        'Parent': 'A00',
        'Related': []
    },
    'A02': {
        'Hex': '0x02',
        'Genre': 'alternative rock',
        'Parent': 'A00',
        'Related': ['A10'] # Related to 'A10' grunge'
    },
    'A03': {
        'Hex': '0x03',
        'Genre': 'indie rock',
        'Parent': 'A00',
        'Related': ['C03']  # Related to 'C03' indie pop
    },
    'A04': {
        'Hex': '0x04',
        'Genre': 'folk rock',
        'Parent': 'A00',
        'Related': ['B00', 'B06', 'B07', 'A20']  # Related to 'B00' folk, 'B06' acoustic folk, 'B07' piano folk, and 'A20' country rock
    },
    'A05': {
        'Hex': '0x05',
        'Genre': 'mellow rock',
        'Parent': 'A00',
        'Related': []
    },
    'A06': {
        'Hex': '0x06',
        'Genre': 'acoustic rock',
        'Parent': 'A00',
        'Related': []
    },
    'A07': {
        'Hex': '0x07',
        'Genre': 'piano rock',
        'Parent': 'A00',
        'Related': ['B07']  # Related to 'B07' piano folk'
    },
    'A08': {
        'Hex': '0x08',
        'Genre': 'pop rock',
        'Parent': 'A00',
        'Related': []
    },
    'A09': {
        'Hex': '0x09',
        'Genre': 'hard rock',
        'Parent': 'A00',
        'Related': ['A10', 'A11', 'A12'] # Related to 'A10' grunge, 'A11' metal, and 'A12' hardcare
    },
    'A10': {
        'Hex': '0x0A',
        'Genre': 'grunge',
        'Parent': 'A00',
        'Related': ['A02', 'A09', 'A11', 'A12'] # Related to 'A02' alternative rock, 'A09' hard rock, 'A11' metal, and 'A12' hardcare
    },
    'A11': {
        'Hex': '0x0B',
        'Genre': 'metal',
        'Parent': 'A00',
        'Related': []
    },
    'A12': {
        'Hex': '0x0C',
        'Genre': 'hardcore',
        'Parent': 'A00',
        'Related': []
    },
    'A13': {
        'Hex': '0x0D',
        'Genre': 'emo',
        'Parent': 'A00',
        'Related': []
    },
    'A14': {
        'Hex': '0x0E',
        'Genre': 'jam band',
        'Parent': 'A00',
        'Related': []
    },
    'A15': {
        'Hex': '0x0F',
        'Genre': 'ska punk',
        'Parent': 'A00',
        'Related': ['A16']  # Related to 'A16' punk
    },
    'A16': {
        'Hex': '0x10',
        'Genre': 'punk',
        'Parent': 'A00',
        'Related': ['A15', 'C16']  # Related to 'A15' ska punk and 'C16' pop punk
    },
    'A17': {
        'Hex': '0x11',
        'Genre': 'surf rock',
        'Parent': 'A00',
        'Related': []
    },
    'A18': {
        'Hex': '0x12',
        'Genre': 'funk rock',
        'Parent': 'A00',
        'Related': []
    },
    'A19': {
        'Hex': '0x13',
        'Genre': 'rock & roll',
        'Parent': 'A00',
        'Related': []
    },
    'A20': {
        'Hex': '0x14',
        'Genre': 'country rock',
        'Parent': 'A00',
        'Related': ['B00']  # Related to 'B00' folk
    },
    'A21': {
        'Hex': '0x15',
        'Genre': 'blues rock',
        'Parent': 'A00',
        'Related': ['H00']  # Related to 'H00' blues
    },
    'A22': {
        'Hex': '0x16',
        'Genre': 'rap rock',
        'Parent': 'A00',
        'Related': ['I00'] # Related to 'I00' hip-hop
    },
    'A23': {
        'Hex': '0x17',
        'Genre': 'rock electronica',
        'Parent': 'A00',
        'Related': ['J00']  # Related to 'J00' electronic'
    },
    'B00': {
        'Hex': '0x18',
        'Genre': 'folk',
        'Parent': None,
        'Related': ['A04']  # Related to 'A04' folk rock
    },
    'B01': {
        'Hex': '0x19',
        'Genre': 'singer-songwriter',
        'Parent': 'B00',
        'Related': []
    },
    'B02': {
        'Hex': '0x1A',
        'Genre': 'world music',
        'Parent': None,
        'Related': []
    },
    'B03': {
        'Hex': '0x1B',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'B04': {
        'Hex': '0x1C',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'B05': {
        'Hex': '0x1D',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'B06': {
        'Hex': '0x1E',
        'Genre': 'acoustic folk',
        'Parent': 'B00',
        'Related': []
    },
    'B07': {
        'Hex': '0x1F',
        'Genre': 'piano folk',
        'Parent': 'B00',
        'Related': []
    },
    'B08': {
        'Hex': '0x20',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'B09': {
        'Hex': '0x21',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'B10': {
        'Hex': '0x22',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'B11': {
        'Hex': '0x23',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'B12': {
        'Hex': '0x24',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'B13': {
        'Hex': '0x25',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'B14': {
        'Hex': '0x26',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'B15': {
        'Hex': '0x27',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'B16': {
        'Hex': '0x28',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'B17': {
        'Hex': '0x29',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'B18': {
        'Hex': '0x2A',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'B19': {
        'Hex': '0x2B',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'B20': {
        'Hex': '0x2C',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'B21': {
        'Hex': '0x2D',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'B22': {
        'Hex': '0x2E',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'B23': {
        'Hex': '0x2F',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C00': {
        'Hex': '0x30',
        'Genre': 'pop',
        'Parent': None,
        'Related': []
    },
    'C01': {
        'Hex': '0x31',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C02': {
        'Hex': '0x32',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C03': {
        'Hex': '0x33',
        'Genre': 'indie pop',
        'Parent': 'C00',
        'Related': ['A03']  # Related to 'A03' indie rock
    },
    'C04': {
        'Hex': '0x34',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C05': {
        'Hex': '0x35',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C06': {
        'Hex': '0x36',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C07': {
        'Hex': '0x37',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C08': {
        'Hex': '0x38',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C09': {
        'Hex': '0x39',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C10': {
        'Hex': '0x3A',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C11': {
        'Hex': '0x3B',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C12': {
        'Hex': '0x3C',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C13': {
        'Hex': '0x3D',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C14': {
        'Hex': '0x3E',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C15': {
        'Hex': '0x3F',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C16': {
        'Hex': '0x40',
        'Genre': 'pop punk',
        'Parent': 'C00',
        'Related': ['A15', 'A16']  # Related to 'A15' ska punk and 'A16' punk
    },
    'C17': {
        'Hex': '0x41',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C18': {
        'Hex': '0x42',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C19': {
        'Hex': '0x43',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C20': {
        'Hex': '0x44',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C21': {
        'Hex': '0x45',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C22': {
        'Hex': '0x46',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'C23': {
        'Hex': '0x47',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'D00': {
        'Hex': '0x48',
        'Genre': 'jazz',
        'Parent': None,
        'Related': []
    },
    'D01': {
        'Hex': '0x49',
        'Genre': 'vocal jazz',
        'Parent': 'D00',
        'Related': []
    },
    'D02': {
        'Hex': '0x4A',
        'Genre': 'swing',
        'Parent': 'D00',
        'Related': []
    },
    'D03': {
        'Hex': '0x4B',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'D04': {
        'Hex': '0x4C',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'D05': {
        'Hex': '0x4D',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'D06': {
        'Hex': '0x4E',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'D07': {
        'Hex': '0x4F',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'D08': {
        'Hex': '0x50',
        'Genre': 'jazz pop',
        'Parent': 'D00',
        'Related': []
    },
    'D09': {
        'Hex': '0x51',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'D10': {
        'Hex': '0x52',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'D11': {
        'Hex': '0x53',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'D12': {
        'Hex': '0x54',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'D13': {
        'Hex': '0x55',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'D14': {
        'Hex': '0x56',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'D15': {
        'Hex': '0x57',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'D16': {
        'Hex': '0x58',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'D17': {
        'Hex': '0x59',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'D18': {
        'Hex': '0x5A',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'D19': {
        'Hex': '0x5B',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'D20': {
        'Hex': '0x5C',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'D21': {
        'Hex': '0x5D',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'D22': {
        'Hex': '0x5E',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'D23': {
        'Hex': '0x5F',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'E00': {
        'Hex': '0x60',
        'Genre': 'reggae',
        'Parent': None,
        'Related': ['E01']  # Related to 'E01' dub
    },
    'E01': {
        'Hex': '0x61',
        'Genre': 'dub',
        'Parent': 'E00',
        'Related': ['E00']  # Related to 'E00' reggae
    },
    'E02': {
        'Hex': '0x62',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'E03': {
        'Hex': '0x63',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'E04': {
        'Hex': '0x64',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'E05': {
        'Hex': '0x65',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'E06': {
        'Hex': '0x66',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'E07': {
        'Hex': '0x67',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'E08': {
        'Hex': '0x68',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'E09': {
        'Hex': '0x69',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'E10': {
        'Hex': '0x6A',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'E11': {
        'Hex': '0x6B',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'E12': {
        'Hex': '0x6C',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'E13': {
        'Hex': '0x6D',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'E14': {
        'Hex': '0x6E',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'E15': {
        'Hex': '0x6F',
        'Genre': 'ska',
        'Parent': None,
        'Related': ['A16']  # Related to 'A16' punk
    },
    'E16': {
        'Hex': '0x70',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'E17': {
        'Hex': '0x71',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'E18': {
        'Hex': '0x72',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'E19': {
        'Hex': '0x73',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'E20': {
        'Hex': '0x74',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'E21': {
        'Hex': '0x75',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'F00': {
        'Hex': '0x76',
        'Genre': 'r&b',
        'Parent': None,
        'Related': ['F01', 'F18']  # Related to 'F01' soul and 'F18' funk
    },
    'F01': {
        'Hex': '0x77',
        'Genre': 'soul',
        'Parent': 'F00',
        'Related': ['F00']
    },
    'F02': {
        'Hex': '0x78',
        'Genre': 'gospel',
        'Parent': 'F00',
        'Related': []
    },
    'F03': {
        'Hex': '0x79',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'F04': {
        'Hex': '0x7A',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'F05': {
        'Hex': '0x7B',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'F06': {
        'Hex': '0x7C',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'F07': {
        'Hex': '0x7D',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'F08': {
        'Hex': '0x7E',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'F09': {
        'Hex': '0x7F',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'F10': {
        'Hex': '0x80',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'F11': {
        'Hex': '0x81',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'F12': {
        'Hex': '0x82',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'F13': {
        'Hex': '0x83',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'F14': {
        'Hex': '0x84',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'F15': {
        'Hex': '0x85',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'F16': {
        'Hex': '0x86',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'F17': {
        'Hex': '0x87',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'F18': {
        'Hex': '0x88',
        'Genre': 'funk',
        'Parent': 'F00',
        'Related': []
    },
    'F19': {
        'Hex': '0x89',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'F20': {
        'Hex': '0x8A',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'F21': {
        'Hex': '0x8B',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G00': {
        'Hex': '0x8C',
        'Genre': 'country',
        'Parent': None,
        'Related': ['A20']  # Related to 'A20' country rock
    },
    'G01': {
        'Hex': '0x8D',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G02': {
        'Hex': '0x8E',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G03': {
        'Hex': '0x8F',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G04': {
        'Hex': '0x90',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G05': {
        'Hex': '0x91',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G06': {
        'Hex': '0x92',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G07': {
        'Hex': '0x93',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G08': {
        'Hex': '0x94',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G09': {
        'Hex': '0x95',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G10': {
        'Hex': '0x96',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G11': {
        'Hex': '0x97',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G12': {
        'Hex': '0x98',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G13': {
        'Hex': '0x99',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G14': {
        'Hex': '0x9A',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G15': {
        'Hex': '0x9B',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G16': {
        'Hex': '0x9C',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G17': {
        'Hex': '0x9D',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G18': {
        'Hex': '0x9E',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G19': {
        'Hex': '0x9F',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G20': {
        'Hex': '0xA0',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'G21': {
        'Hex': '0xA1',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H00': {
        'Hex': '0xA2',
        'Genre': 'blues',
        'Parent': None,
        'Related': ['A21']  # Related to 'A21' blues rock
    },
    'H01': {
        'Hex': '0xA3',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H02': {
        'Hex': '0xA4',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H03': {
        'Hex': '0xA5',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H04': {
        'Hex': '0xA6',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H05': {
        'Hex': '0xA7',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H06': {
        'Hex': '0xA8',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H07': {
        'Hex': '0xA9',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H08': {
        'Hex': '0xAA',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H09': {
        'Hex': '0xAB',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H10': {
        'Hex': '0xAC',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H11': {
        'Hex': '0xAD',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H12': {
        'Hex': '0xAE',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H13': {
        'Hex': '0xAF',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H14': {
        'Hex': '0xB0',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H15': {
        'Hex': '0xB1',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H16': {
        'Hex': '0xB2',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H17': {
        'Hex': '0xB3',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H18': {
        'Hex': '0xB4',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H19': {
        'Hex': '0xB5',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H20': {
        'Hex': '0xB6',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'H21': {
        'Hex': '0xB7',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I00': {
        'Hex': '0xB8',
        'Genre': 'hip-hop',
        'Parent': None,
        'Related': []
    },
    'I01': {
        'Hex': '0xB9',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I02': {
        'Hex': '0xBA',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I03': {
        'Hex': '0xBB',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I04': {
        'Hex': '0xBC',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I05': {
        'Hex': '0xBD',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I06': {
        'Hex': '0xBE',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I07': {
        'Hex': '0xBF',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I08': {
        'Hex': '0xC0',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I09': {
        'Hex': '0xC1',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I10': {
        'Hex': '0xC2',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I11': {
        'Hex': '0xC3',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I12': {
        'Hex': '0xC4',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I13': {
        'Hex': '0xC5',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I14': {
        'Hex': '0xC6',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I15': {
        'Hex': '0xC7',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I16': {
        'Hex': '0xC8',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I17': {
        'Hex': '0xC9',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I18': {
        'Hex': '0xCA',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I19': {
        'Hex': '0xCB',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I20': {
        'Hex': '0xCC',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I21': {
        'Hex': '0xCD',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I22': {
        'Hex': '0xCE',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'I23': {
        'Hex': '0xCF',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'J00': {
        'Hex': '0xD0',
        'Genre': 'electronic',
        'Parent': None,
        'Related': []
    },
    'J01': {
        'Hex': '0xD1',
        'Genre': 'edm',
        'Parent': 'J00',
        'Related': []
    },
    'J02': {
        'Hex': '0xD2',
        'Genre': 'house',
        'Parent': 'J00',
        'Related': []
    },
    'J03': {
        'Hex': '0xD3',
        'Genre': 'techno',
        'Parent': 'J00',
        'Related': []
    },
    'J04': {
        'Hex': '0xD4',
        'Genre': 'disco',
        'Parent': 'J00',
        'Related': []
    },
    'J05': {
        'Hex': '0xD5',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'J06': {
        'Hex': '0xD6',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'J07': {
        'Hex': '0xD7',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'J08': {
        'Hex': '0xD8',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'J09': {
        'Hex': '0xD9',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'J10': {
        'Hex': '0xDA',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'J11': {
        'Hex': '0xDB',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'J12': {
        'Hex': '0xDC',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'J13': {
        'Hex': '0xDD',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'J14': {
        'Hex': '0xDE',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'J15': {
        'Hex': '0xDF',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'J16': {
        'Hex': '0xE0',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'J17': {
        'Hex': '0xE1',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'J18': {
        'Hex': '0xE2',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'J19': {
        'Hex': '0xE3',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'J20': {
        'Hex': '0xE4',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'J21': {
        'Hex': '0xE5',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'J22': {
        'Hex': '0xE6',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'J23': {
        'Hex': '0xE7',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'K00': {
        'Hex': '0xE8',
        'Genre': 'classical',
        'Parent': None,
        'Related': []
    },
    'K01': {
        'Hex': '0xE9',
        'Genre': 'orchestral',
        'Parent': 'K00',
        'Related': []
    },
    'K02': {
        'Hex': '0xEA',
        'Genre': 'opera',
        'Parent': 'K00',
        'Related': []
    },
    'K03': {
        'Hex': '0xEB',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'K04': {
        'Hex': '0xEC',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'K05': {
        'Hex': '0xED',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'K06': {
        'Hex': '0xEE',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'K07': {
        'Hex': '0xEF',
        'Genre': 'piano',
        'Parent': 'K00',
        'Related': []
    },
    'K08': {
        'Hex': '0xF0',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'K09': {
        'Hex': '0xF1',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'K10': {
        'Hex': '0xF2',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'K11': {
        'Hex': '0xF3',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'K12': {
        'Hex': '0xF4',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'K13': {
        'Hex': '0xF5',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'K14': {
        'Hex': '0xF6',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'K15': {
        'Hex': '0xF7',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'K16': {
        'Hex': '0xF8',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'K17': {
        'Hex': '0xF9',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'K18': {
        'Hex': '0xFA',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'K19': {
        'Hex': '0xFB',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'K20': {
        'Hex': '0xFC',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'K21': {
        'Hex': '0xFD',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'K22': {
        'Hex': '0xFE',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
    'K23': {
        'Hex': '0xFF',
        'Genre': '',
        'Parent': None,
        'Related': []
    },
}

# Generate a reverse mapping: subgenre_code -> parent_genre_code
subgenre_to_parent = {
    key: details['Parent']
    for key, details in genre_mapping.items()
    if details['Parent'] is not None and details['Genre']
}

__all__ = ['genre_mapping', 'subgenre_to_parent']
