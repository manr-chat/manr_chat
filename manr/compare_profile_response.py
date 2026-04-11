#!/usr/bin/env python3
"""
Compare profile data returned from the location grid, i.e. "cascade",
and from fetching a profiles via their IDs. Unfortunately, these methods
return different subsets of the full profile data, sometimes with different
names or different capitalization. Also, fetching multiple profiles at once
returns less data than fetching individual profiles, except for "acceptNSFWPics",
which is apparently missing from fetching individual profiles.
For empty data, sometimes profile contains null while cascade is missing the field.
What a mess! 🙄🙄🙄
"""


from .logindata import *

def collect_profiles(data):
    profiles = data["items"]
    full, partial = [], []
    for p in profiles:
        if "full_profile_v1" == p["type"]:
            full.append(p["data"])
        elif "partial_profile_v1" == p["type"]:
            partial.append(p["data"])
    return full, partial

def get_ids(profiles):
    return [p["profileId"] for p in profiles]

def compare_keys_data(grid_profiles, fetch_profiles):
    #print("grid_profiles:", grid_profiles[:2])
    #print("fetch_profiles:", fetch_profiles[:2])
    grid_keys = set(flatten([p.keys() for p in grid_profiles]))
    fetch_keys = set(flatten([p.keys() for p in fetch_profiles]))
    #print("grid_keys:\n", grid_keys)
    #print("fetch_keys:\n", fetch_keys)
    all_keys = list(sorted(list(grid_keys | fetch_keys)))
    #print("all_keys:\n", all_keys)
    both, grid_only, fetch_only, none = set(), set(), set(), set()
    grid = {str(p["profileId"]): p for p in grid_profiles}
    fetch = {str(p["profileId"]): p for p in fetch_profiles}
    #print("len(grid):", len(grid))
    #print("len(fetch):", len(fetch))
    #print("grid.keys():", grid.keys())
    #print("fetch.keys():", fetch.keys())
    assert set(grid.keys()) == set(fetch.keys())
    for id in grid.keys():
        gp, fp = grid[id], fetch[id]
        for k in all_keys:
            gp_has_key = k in gp
            fp_has_key = k in fp
            if gp_has_key and fp_has_key:
                both.add(k)
            if gp_has_key and not fp_has_key:
                grid_only.add(k)
            if not gp_has_key and fp_has_key:
                fetch_only.add(k)
            if not gp_has_key and not fp_has_key:
                none.add(k)
    return all_keys, both, grid_only, fetch_only, none

def print_comparison(all_keys, both, grid_only, fetch_only, none):
    max_key_len = max([len(str(k)) for k in all_keys])
    print("".ljust(max_key_len) + "    BOTH  NONE  GRID  FETCH")
    marker = lambda found: "*" if found else " "
    for k in all_keys:
        print(f"{k: <{max_key_len}}:    {marker(k in both)}     {marker(k in none)}     {marker(k in grid_only)}      {marker(k in fetch_only)}  ")

def compare_keys(grid_profiles, fetch_profiles):
    all_keys, both, grid_only, fetch_only, none = compare_keys_data(grid_profiles, fetch_profiles)
    print_comparison(all_keys, both, grid_only, fetch_only, none)

def get_profiles_individually(id_list):
    profiles = []
    for id in id_list:
        data = user.get_profile(str(id))
        profiles += data["profiles"]
    return profiles


def collect_data_from_server():
    max_request_size = 150
    cres = user.getProfiles(*BKTH)
    full, partial = collect_profiles(cres)
    partial = partial[:max_request_size]
    full = full[:10]
    partial = partial[:10]
    full_ids = get_ids(full)
    partial_ids = get_ids(partial)
    full_profiles_at_once = user.get_profiles(full_ids)["profiles"]
    partial_profiles_at_once = user.get_profiles(partial_ids)["profiles"]
    full_profiles = get_profiles_individually(full_ids)
    partial_profiles = get_profiles_individually(partial_ids)
    return full, full_profiles, full_profiles_at_once, partial, partial_profiles, partial_profiles_at_once

def save_data_to_files(full, full_profiles, full_profiles_at_once, partial, partial_profiles, partial_profiles_at_once):
    save_json("data/full_cascade.json", full)
    save_json("data/full_profiles.json", full_profiles)
    save_json("data/full_profiles_at_once.json", full_profiles_at_once)
    save_json("data/partial_cascade.json", partial)
    save_json("data/partial_profiles.json", partial_profiles)
    save_json("data/partial_profiles_at_once.json", partial_profiles_at_once)

def read_data_from_files():
    full = load_json("data/full_cascade.json")
    full_profiles = load_json("data/full_profiles.json")
    full_profiles_at_once = load_json("data/full_profiles_at_once.json")
    partial = load_json("data/partial_cascade.json")
    partial_profiles = load_json("data/partial_profiles.json")
    partial_profiles_at_once = load_json("data/partial_profiles_at_once.json")
    return full, full_profiles, full_profiles_at_once, partial, partial_profiles, partial_profiles_at_once

def compare_grid_and_fetch_profile_data():
    if False:
        full, full_profiles, full_profiles_at_once, partial, partial_profiles, partial_profiles_at_once = collect_data_from_server()
        save_data_to_files(full, full_profiles, full_profiles_at_once, partial, partial_profiles, partial_profiles_at_once)
    else:
        full, full_profiles, full_profiles_at_once, partial, partial_profiles, partial_profiles_at_once = read_data_from_files()
    print("For full profiles:")
    compare_keys(full, full_profiles)
    print("For partial profiles:")
    compare_keys(partial, partial_profiles)
    print("For full profiles at once:")
    compare_keys(full, full_profiles_at_once)
    print("For partial profiles at once:")
    compare_keys(partial, partial_profiles_at_once)

if __name__ == "__main__":
    compare_grid_and_fetch_profile_data()