import time

# try importing spidev
try:
    import spidev

except ImportError:
    print("spidev module not found, installing it...")

    try :
        import subprocess
        subprocess.check_call("pip3 install spidev", shell=True)  # install spidev module
        import spidev
    
    except:
        print("spidev module cannot be installed, SPI is disabled !")
        pass


def spi_send(data, spi_mode, spi_speed, spi_sleep, spi_device, spi_port):
    """
    Send data to SPI port

    Args:
        data (list): list of bytes to send
        spi_mode (int): SPI mode
        spi_speed (int): SPI speed
        spi_sleep (float): sleep time in seconds
    
    Returns:
        None
    """

    try:
        
        spi = spidev.SpiDev()  # create spi object
        spi.open(spi_port, spi_device)  # open spi port 0, device (CS) 0
        spi.mode = spi_mode  # set SPI mode
        spi.max_speed_hz = spi_speed  # set SPI speed
        # spi.cshigh = False
        # spi.bits_per_word = 8

        spi.writebytes(data)  # write data to SPI
        time.sleep(spi_sleep)  # sleep for n seconds

    except:
        print("SPI send failed !")

    finally:
        try:
            spi.close() # close SPI port if it was opened
        except:
            pass


def spi_remap(c):
    """
    Remap class ID for Embeeded requirements

    Args:
        c (int): class ID

    Returns:
        int: remaped class ID

    Note:
        Speed Limits have most significant bit set to 1, and other signs have it set to 0
        Speed Limit: 9-19
        other signs: 0-8, 128-137
    """

    class_map = {
        9  : 100,
        10 : 120,
        11 : 20,
        12 : 30,
        13 : 40,
        14 : 50,
        15 : 60,
        16 : 70,
        17 : 80,
        18 : 90,
        19 : 9,
        20 : 10}

    if c in class_map.keys():
        if c >= 9 and c <= 18:
            c = class_map[c] + 128
        else:
            c = class_map[c]

    return c