import numpy as np

def compute_stance_flip_probability(metrics: dict) -> float:
    """
    Computes the concurrent probability of a conversational stance flip
    using the extracted beta coefficients from a Generalized Linear Model.
    
    Parameters:
        metrics (dict): A dictionary containing the linguistic scores 
                        for the current conversational turn.
                        
    Returns:
        float: The calculated probability score bounded between 0 and 1.
    """
    # Replace these placeholder values with the exact estimates from your Table 10 Pooled column
    coefficients = {
        "intercept": 1.5319814,
        "assent": -2.2665871,
        "we": 0.5937186,
        "Clout": -0.0103447,
        "moral": 0.1537449,
        "adj": -0.0684780,
        "negate": 0.2930279,
        "risk": -0.1574600,
        "Tone": 0.0008074,
        #"assent_diff": 1.1855741,
    }
    
    # Begin the linear combination with the baseline intercept weight
    log_odds = coefficients["intercept"]
    
    # Sequentially multiply each incoming metric by its corresponding beta weight
    for metric_name, metric_value in metrics.items():
        if metric_name in coefficients:
            log_odds += coefficients[metric_name] * metric_value
            
    # Apply the standard mathematical sigmoid mapping to generate the final probability
    # Take the opposite as we are modeling the probability of a stance flip (i.e., 1 - P(no flip))
    probability = 1 - 1 / (1 + np.exp(-log_odds))
    return float(probability)