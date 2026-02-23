import random
import math
import matplotlib.pyplot as plt

def generate_poisson(lam, n):
    results = []
    l_val = math.exp(-lam)
    for _ in range(n):
        k = 0
        p = 1.0
        while p > l_val:
            k += 1
            p *= (1.0 - random.random())
        results.append(k - 1)
    return results

def generate_normal(mu, sigma, n):
    results = []
    for _ in range(n):
        u1 = 1.0 - random.random()
        u2 = random.random()
        z0 = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
        results.append(z0 * sigma + mu)
    return results

def main():
    try:
        lam = float(input("Podaj wartosc lambda dla rozkladu Poissona: "))
        mu = float(input("Podaj srednia dla rozkladu normalnego: "))
        sigma = float(input("Podaj odchylenie standardowe dla rozkladu normalnego: "))
        n = int(input("Podaj ilosc liczb do wygenerowania: "))
        seed_input = input("Podaj ziarno (puste = brak ziarna): ")
        
        if seed_input.strip():
            random.seed(int(seed_input))
        
        poisson_data = generate_poisson(lam, n)
        normal_data = generate_normal(mu, sigma, n)
        
        plt.figure(figsize=(10, 5))
        
        plt.subplot(1, 2, 1)
        max_p = int(max(poisson_data))
        plt.hist(poisson_data, bins=range(max_p + 2), density=True, color='blue', edgecolor='black', align='left')
        plt.title(f"Rozklad Poissona (lambda={lam})")
        
        plt.subplot(1, 2, 2)
        plt.hist(normal_data, bins=50, density=True, color='green', edgecolor='black')
        plt.title(f"Rozklad Normalny (mu={mu}, sigma={sigma})")
        
        plt.tight_layout()
        plt.show()
    except ValueError:
        print("Wprowadzono nieprawidlowe dane.")

if __name__ == "__main__":
    main()