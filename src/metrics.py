"""Metrics and scene-level bootstrap, implementing section 8 of docs/decision_rules.md.

All metrics are in cells (the model output x 100 has already been applied).

The bootstrap resamples SCENES, not images: images of one scene share a layout, so they are not
independent, and resampling single images would give intervals that are too narrow.

Self-test on synthetic numbers (reads no data):
    .venv\\Scripts\\python.exe -m src.metrics
"""

import numpy as np

from src.common import load_rules

# Bootstrap settings come from the frozen rules, so they exist in one place only.
BOOTSTRAP = load_rules()["evaluation"]["bootstrap"]
N_BOOT = BOOTSTRAP["n"]  # B = 10,000
SEED = BOOTSTRAP["seed"]  # 42
CI = BOOTSTRAP["ci"]  # 0.95


def mae(y_true, y_pred):
    """Mean absolute error."""
    return float(np.mean(np.abs(np.asarray(y_true) - np.asarray(y_pred))))


def rmse(y_true, y_pred):
    """Root mean squared error."""
    return float(np.sqrt(np.mean((np.asarray(y_true) - np.asarray(y_pred)) ** 2)))


def r2(y_true, y_pred):
    """Coefficient of determination: 1 - SS_residual / SS_total."""
    y_true = np.asarray(y_true)
    ss_residual = np.sum((y_true - np.asarray(y_pred)) ** 2)
    ss_total = np.sum((y_true - y_true.mean()) ** 2)
    return float(1 - ss_residual / ss_total)


def scene_groups(scene_ids):
    """Return one array of image indices per scene, in sorted scene order."""
    scene_ids = np.asarray(scene_ids)
    return [np.flatnonzero(scene_ids == scene) for scene in np.unique(scene_ids)]


def scene_resamples(scene_ids, n_boot=N_BOOT, seed=SEED):
    """Yield n_boot arrays of image indices.

    Each resample draws as many scenes as there are, with replacement, and takes all images of
    every drawn scene. The same scene_ids and seed always give the same resamples, which is what
    makes two models paired.
    """
    groups = scene_groups(scene_ids)
    rng = np.random.default_rng(seed)
    for _ in range(n_boot):
        drawn = rng.integers(0, len(groups), size=len(groups))
        yield np.concatenate([groups[scene] for scene in drawn])


def percentile_interval(values, ci=CI):
    """Return the (low, high) percentile interval of the bootstrap values."""
    tail = (1 - ci) / 2 * 100
    low, high = np.percentile(values, [tail, 100 - tail])
    return float(low), float(high)


def bootstrap_ci(y_true, y_pred, scene_ids, metric, n_boot=N_BOOT, seed=SEED, ci=CI):
    """Return {"point", "low", "high"} for one metric of one model."""
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    values = [
        metric(y_true[index], y_pred[index]) for index in scene_resamples(scene_ids, n_boot, seed)
    ]
    low, high = percentile_interval(values, ci)
    return {"point": metric(y_true, y_pred), "low": low, "high": high}


def bootstrap_ratio_ci(y_true, pred_a, pred_b, scene_ids, metric=mae, n_boot=N_BOOT, seed=SEED, ci=CI):
    """Paired interval of metric(model a) / metric(model b), e.g. MAE_own / MAE_best.

    Both models are scored on the same resampled scenes inside one loop.
    """
    y_true, pred_a, pred_b = np.asarray(y_true), np.asarray(pred_a), np.asarray(pred_b)
    values = [
        metric(y_true[index], pred_a[index]) / metric(y_true[index], pred_b[index])
        for index in scene_resamples(scene_ids, n_boot, seed)
    ]
    low, high = percentile_interval(values, ci)
    return {"point": metric(y_true, pred_a) / metric(y_true, pred_b), "low": low, "high": high}


def self_test():
    """Check everything on synthetic numbers. Raises AssertionError on a failure."""
    # Metrics, worked by hand: errors 0, 0, 0, 1 and y has SS_total = 5.
    y_true, y_pred = [1, 2, 3, 4], [1, 2, 3, 5]
    assert np.isclose(mae(y_true, y_pred), 0.25)
    assert np.isclose(rmse(y_true, y_pred), 0.5)
    assert np.isclose(r2(y_true, y_pred), 0.8)

    # Settings must match section 8.
    assert (N_BOOT, SEED, CI) == (10000, 42, 0.95)

    # 50 scenes of 4 images each. One random error per scene, shared by its images.
    rng = np.random.default_rng(0)
    n_scenes, n_images = 50, 4
    scene_ids = np.repeat([f"s{i:02d}" for i in range(n_scenes)], n_images)
    y_true = np.repeat(rng.uniform(0, 100, n_scenes), n_images)
    y_pred = y_true + np.repeat(rng.normal(0, 5, n_scenes), n_images)
    n_boot = 2000  # Enough here, and keeps the test under a few seconds.

    # A scene is never split: within a resample every scene appears 4, 8, 12... times.
    for index in scene_resamples(scene_ids, n_boot=20, seed=1):
        assert len(index) == n_scenes * n_images
        _, times = np.unique(scene_ids[index], return_counts=True)
        assert np.all(times % n_images == 0)

    # The same seed repeats the interval exactly; another seed does not.
    first = bootstrap_ci(y_true, y_pred, scene_ids, mae, n_boot=n_boot)
    assert first == bootstrap_ci(y_true, y_pred, scene_ids, mae, n_boot=n_boot)
    assert first != bootstrap_ci(y_true, y_pred, scene_ids, mae, n_boot=n_boot, seed=1)
    assert first["low"] < first["point"] < first["high"]

    # Pretending every image is its own scene must give a narrower interval, as errors repeat.
    wrong = bootstrap_ci(y_true, y_pred, np.arange(len(y_true)), mae, n_boot=n_boot)
    assert first["high"] - first["low"] > wrong["high"] - wrong["low"]

    # Paired: errors of b are exactly half those of a, so every paired resample gives 2.
    pred_b = y_true + (y_pred - y_true) / 2
    ratio = bootstrap_ratio_ci(y_true, y_pred, pred_b, scene_ids, n_boot=n_boot)
    assert np.isclose(ratio["point"], 2) and np.isclose(ratio["low"], 2)
    assert np.isclose(ratio["high"], 2)

    print("metrics self-test: PASS")


if __name__ == "__main__":
    self_test()
