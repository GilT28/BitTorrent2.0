import math
import time
from tqdm import tqdm


results = []

for i in tqdm(range(10000)):
    results.append(math.factorial(i))