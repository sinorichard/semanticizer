# Copyright 2012-2013, University of Amsterdam. This program is free software:
# you can redistribute it and/or modify it under the terms of the GNU Lesser 
# General Public License as published by the Free Software Foundation, either 
# version 3 of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or 
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License 
# for more details.
# 
# You should have received a copy of the GNU Lesser General Public License 
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import joblib
import os, yaml
import sklearn.metrics

def compute_metrics(labels, scores, threshold=0.5):
    metrics = {}
    # Sort according to score
    scores, labels = zip(*sorted(zip(scores, labels)))
    predictions = [score >= threshold for score in scores]    
    # Classification metrics
    metrics["precision"], metrics["recall"], metrics["f1"], support = \
        sklearn.metrics.precision_recall_fscore_support(labels, predictions, \
                                                        average="weighted")
    metrics["accuracy"] = sklearn.metrics.accuracy_score(labels, predictions)
    metrics["zeroOneLoss"] = sklearn.metrics.zero_one_loss(labels, predictions)
    # Rank-based metrics
    metrics["averagePrecision"] = \
        sklearn.metrics.average_precision_score(labels, scores)
    metrics["ROC AUC"] = sklearn.metrics.roc_auc_score(labels, scores)
    # R-precision
    r_labels = labels[-support:]
    r_predictions = [True for label in r_labels]
    metrics["rPrecision"] = \
        sklearn.metrics.precision_score(r_labels, r_predictions)
    return metrics

class ModelStore():
    def __init__(self, model_dir):
        self.model_dir = model_dir
        self.model_cache = {}

    def load_model(self, modelname):
        if modelname.endswith(".pkl"):
            return self.load_model(modelname[:-4])

        if modelname in self.model_cache:
            return self.model_cache[modelname]

        modelfile = os.path.join(self.model_dir, modelname)
        model = joblib.load(modelfile + ".pkl")

        description = {"name": modelname, "source": modelfile + ".pkl"}
        if os.path.exists(modelfile + ".yaml"):
            description.update(yaml.load(file(modelfile + ".yaml")))

        self.model_cache[modelname] = (model, description)
        return (model, description)

    def save_model(self, model, modelname, description=None):
        if modelname.endswith(".pkl"):
            modelname = modelname[:-4]

        modelfile = os.path.join(self.model_dir, modelname)
        joblib.dump(model, modelfile + ".pkl")

        if description != None:
            with open(modelfile + ".yaml", 'w') as out:
                out.write(yaml.dump(description, Dumper=yaml.CDumper))
        else:
            description = {}
        
        description.update({"name": modelname, "source": modelfile + ".pkl"})
        self.model_cache[modelname] = (model, description)
            
    def _convert_dict(self, data, skip=[]):
        """Helper function that convert the values of dictionary to int/float. 
           Optionally you can skip a list of values."""
        converted_data = {}
        for k,v in data.iteritems():
            if k in skip: continue
            try:
                converted_data[k] = int("".join(v))
            except ValueError:
                try:
                    converted_data[k] = float("".join(v))
                except ValueError:
                    converted_data[k] = v
        return converted_data    

    def create_model(self, settings, skip_settings=[]):
        if not "classifier" in settings:
            raise ValueError("Expecting a classifier in settings.")
        if not "." in settings["classifier"]:
            raise ValueError("Expecting a package in settings.")

        classifier = settings["classifier"].split(".")[-1]
        package = ".".join(settings["classifier"].split(".")[:-1])
    
        # Import package module
        classifier_module = __import__(package, globals(), locals(), \
                                       [str(classifier)], -1)
        # Classifier instance
        Classifier = getattr(classifier_module, classifier)
        
        skip_settings.extend(["classifier"])
        model = Classifier(**self._convert_dict(settings, skip_settings))
        
        return model
