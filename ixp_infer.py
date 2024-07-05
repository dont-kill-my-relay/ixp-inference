"""Infer the IXP (or IXP organisation) on a path of AS.
Data used as input for this script is the following
 - AS path
 - IXP data from CAIDA: https://doi.org/10.21986/CAIDA.DATA.IXPS
"""
import json
import fire
from itertools import pairwise, combinations
import random


def ix_lookup(as_pair: tuple[str, str], ix_state: dict) -> str | None:
    """
    Lookup a pair of ASes in the data structure
    @param as_pair: Pair of ASes to lookup
    @param ix_state: Data structure with the mapping of AS to IXP
    @return: Inferred IXP or IXP organisation if found, else None
    """
    as_pair = (int(as_pair[0]), int(as_pair[1]))
    ix_list = ix_state.get(as_pair, None)
    if isinstance(ix_list, list):
        return random.choice(ix_list)
    return None


def extend_path(path: str, ix_state: dict) -> str:
    if path == "None" or path is None:
        return "None"

    result = ""

    ases = path.split("-")
    for pair in pairwise(ases):
        result += pair[0] + "-"
        ix = ix_lookup(tuple(sorted(pair)), ix_state)

        if ix is not None:
            result += ix + "-"

    return result + ases[-1]


def extend_circuit(aspath_file: str, ix_asns_file: str, ixs_file: str, output_file: str = "ixpath.txt") -> None:
    """
    Extend each circuit made of ASes with inferred IXP in between
    @param aspath_file: File with the AS paths, as show in the README
    @param ix_asns_file: ix-asns*.jsonl from CAIDA: https://publicdata.caida.org/datasets/ixps/
    @param ixs_file: ixs*.jsonl from CAIDA: https://publicdata.caida.org/datasets/ixps/
    @param output_file: Filename for the result
    """
    ix_state = create_data_structure(ix_asns_file, ixs_file)

    print("extending aspath file")
    with open(aspath_file, 'r') as aspath_file, open(output_file, "w") as output_file:
        _ = next(aspath_file)
        for path in aspath_file:
            sample, time, c2g, g2c, e2d, d2e = path.split(" ")
            c2g = extend_path(c2g, ix_state)
            g2c = extend_path(g2c, ix_state)
            e2d = extend_path(e2d, ix_state)
            d2e = extend_path(d2e, ix_state)

            output_file.write(f"{sample} {time} {c2g} {g2c} {e2d} {d2e}")


def create_data_structure(ix_asns_file: str, ixs_file: str) -> dict[tuple, list]:
    """
    From the files provided by CAIDA, build the data structure that is needed for the inference
    @param ix_asns_file: ix-asns*.jsonl from CAIDA: https://publicdata.caida.org/datasets/ixps/
    @param ixs_file: ixs*.jsonl from CAIDA: https://publicdata.caida.org/datasets/ixps/
    @return: mapping from two ASes to the list of IXP or IXP organisations that they can use to connect
    """
    print("building map_ix_to_org")
    map_ix_to_org = dict()
    with open(ixs_file, 'r') as f:
        for line in f.readlines():
            if line.startswith('#'):
                continue
            data = json.loads(line)
            if 'ix_id' not in data:
                print(f'no ix_id in {data}')
            if 'org_id' not in data:
                map_ix_to_org[data['ix_id']] = f"IX{data['ix_id']}"
            else:
                map_ix_to_org[data['ix_id']] = f"ORG{data['org_id']}"

    print("building ix_to_set_asn")
    ix_to_set_asn = dict()
    with open(ix_asns_file, 'r') as f:
        for line in f.readlines():
            if line.startswith('#'):
                continue
            data = json.loads(line)
            ix_id = data['ix_id']
            if ix_id not in map_ix_to_org:
                print(f"{ix_id} not found in map_ix_to_org. Adding it")
                map_ix_to_org[ix_id] = f"IX{ix_id}"

            if ix_id not in ix_to_set_asn:
                ix_to_set_asn[ix_id] = {data['asn']}
            else:
                ix_to_set_asn[ix_id].update({data['asn']})

    print("building asn_pair_to_ix")
    asn_pair_to_ix = dict()
    for ix, asn_set in ix_to_set_asn.items():
        nb_asn_at_ix = len(asn_set)
        for pair in combinations(asn_set, 2):
            pair = tuple(sorted(pair))
            data = {'ix_id': ix, 'nb_asn': nb_asn_at_ix}
            if pair in asn_pair_to_ix:
                asn_pair_to_ix[pair].append(data)
            else:
                asn_pair_to_ix[pair] = [data]

    print("pruning data")
    for pair, ix_list in asn_pair_to_ix.items():
        smallest_nb_asn = min([ix['nb_asn'] for ix in ix_list])
        pruned_list = [ix for ix in ix_list if ix['nb_asn'] == smallest_nb_asn]
        pruned = list({map_ix_to_org[ix['ix_id']] for ix in pruned_list})
        asn_pair_to_ix[pair] = pruned

    return asn_pair_to_ix


if __name__ == '__main__':
    fire.Fire(extend_circuit)