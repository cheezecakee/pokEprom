import os

def make_test_bins():
    structure = {
        'ASUS': {
            'P8Z77-V': ['W25Q64FV_2024-01-15.bin', 'W25Q64FV_2024-02-01.bin'],
            'ROG_Maximus': ['MX25L6406_2023-11-20.bin'],
        },
        'Gigabyte': {
            'Z390_UD': ['W25Q128FV_2024-03-10.bin'],
        },
        'MSI': {
            'B450_Tomahawk': ['W25Q64JV_2023-09-05.bin'],
        },
    }

    for brand, models in structure.items():
        for model, files in models.items():
            path = os.path.join('saves', 'bins', brand, model)
            os.makedirs(path, exist_ok=True)
            for f in files:
                filepath = os.path.join(path, f)
                with open(filepath, 'wb') as fh:
                    fh.write(b'\x00' * 1024)  # dummy 1kb content

    print('Test bins created.')

make_test_bins()
