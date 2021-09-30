def cloud_provider(o):
    if 'gke' in o:
        return 'gke'

    if 'eks' in o:
        return 'eks'

    if 'az' in o:
        return 'aks'

    return None
