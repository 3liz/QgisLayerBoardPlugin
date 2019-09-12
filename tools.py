from os.path import abspath, join, pardir


def resources_path(*args):
    """Get the path to our resources folder.

    :param args List of path elements e.g. ['img', 'logos', 'image.png']
    :type args: str

    :return: Absolute path to the resources folder.
    :rtype: str
    """
    path = abspath(join(__file__, pardir, 'resources'))
    for item in args:
        path = abspath(join(path, item))

    return path
