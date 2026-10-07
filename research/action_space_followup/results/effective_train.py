def train(train, val, seed):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    net = nn.Sequential(nn.Linear(12, 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, ACTIONS))
    target = copy.deepcopy(net)
    opt = torch.optim.Adam(net.parameters(), lr=0.001)
    buffer = []
    best = float('inf')
    saved = None
    history = []
    for episode in range(1, 2001):
        c = train[int(rng.integers(len(train)))]
        inv = 0.5
        h = c['sailing']
        for i in range(4):
            s = state(c, i, inv, h)
            epsilon = max(0.05, 1 - episode / 1500)
            with torch.no_grad():
                a = int(rng.integers(ACTIONS)) if rng.random() < epsilon else int(net(torch.from_numpy(s)).argmax())
            q = quantity(c, i, inv, a)
            inv += q - c['d'][i]
            if q > 1e-09:
                h += c['fixed'][i] + q * c['variable'][i]
            reward = -q * c['p'][i] / 0.1
            done = i == 3
            if done:
                reward += min(c['p']) * inv / 0.1
                reward -= 5 * max(0, h / c['limit'] - 1)
            ns = state(c, min(i + 1, 4), inv, h)
            buffer.append((s, a, reward, ns, float(done)))
            if len(buffer) > 30000:
                buffer.pop(0)
            if len(buffer) >= 128:
                batch = [buffer[j] for j in rng.integers(len(buffer), size=128)]
                ss, aa, rr, nnn, dd = zip(*batch)
                ss = torch.tensor(np.array(ss))
                nsb = torch.tensor(np.array(nnn))
                aa = torch.tensor(aa)
                rr = torch.tensor(rr)
                dd = torch.tensor(dd)
                with torch.no_grad():
                    y = rr + (1 - dd) * target(nsb).gather(1, net(nsb).argmax(1)[:, None]).squeeze(1)
                loss = nn.functional.smooth_l1_loss(net(ss).gather(1, aa[:, None]).squeeze(1), y)
                opt.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(net.parameters(), 10)
                opt.step()
        if episode % 100 == 0:
            target.load_state_dict(net.state_dict())
        if episode % 500 == 0:
            outputs = [rollout(c, net) for c in val]
            score = np.mean([r['cost'] / (c['cap'] * 0.1) + 5 * max(0, r['hours'] / c['limit'] - 1) for c, r in zip(val, outputs)])
            history.append(dict(seed=seed, episode=episode, validation_score=float(score)))
            if score < best:
                best = score
                saved = copy.deepcopy(net.state_dict())
            print(seed, episode, round(score, 6), flush=True)
    net.load_state_dict(saved)
    torch.save({'state_dict': saved, 'seed': seed, 'architecture': [12, 64, 64, ACTIONS], 'source_sha256': SOURCE_SHA, 'efficiency_scenarios': ETAS}, OUT / f'candidate_{seed}.pt')
    return (net, history)
