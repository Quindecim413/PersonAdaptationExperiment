from typing import Any, List
import numpy as np
from sklearn.preprocessing import PolynomialFeatures, StandardScaler, FunctionTransformer, PowerTransformer
from sklearn.feature_selection import SelectFromModel
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from dataclasses import dataclass


NUM_SENSORS = 3

@dataclass(frozen=True)
class ModelCalibrationResult:
    model: Pipeline
    mae: float
    X_all: np.ndarray
    y_all: np.ndarray
    commands_all: np.ndarray

    mask: np.ndarray
    inds_train: np.ndarray
    inds_test: np.ndarray


class GlassesCallibrator:
    def __init__(self) -> None:
        self._calibration_data = {}

    def start_callibrate(self):
        self._calibration_data.clear()

    def add_callibration_data(self, command_code, command_pos, sensor_data):
        if command_code not in self._calibration_data:
            self._calibration_data[command_code] = arr_target, arr_sensor = [], []
        else:
            arr_target, arr_sensor = self._calibration_data[command_code]
        
        arr_target.append(command_pos)
        arr_sensor.append(sensor_data)

    # def additional_functions(self):
    #     pass

    # def 

    def generate_model(self):
        # if self
        x = []
        y = []
        command_codes = []
        for command_code, (arr_target, arr_sensor) in self._calibration_data.items():
            x.extend(arr_sensor)
            y.extend(arr_target)
            command_codes.extend(np.repeat(command_code, len(arr_target)))
        
        clf = Pipeline([
            ('scaler', StandardScaler()),
            ('outlier_detector', IsolationForest(random_state=42))
            ])
        
        X = np.array(x).reshape(-1, NUM_SENSORS)
        y = np.array(y).reshape(-1, 2)
        command_codes = np.array(command_codes, dtype=int)
        print('command_codes', command_codes)
        # assert command_codes.ndim == 1

        mask = clf.fit_predict(X)

        model_pipeline = Pipeline([
            ('scaler', StandardScaler()),
            # ('polyfeatures', PolynomialFeatures(2)),
            # ('tan', FunctionTransformer(np.sinh)),
            # ('power', PowerTransformer()),
            ('regression', Ridge())
        ])

        X_masked = X[mask>0]
        y_masked = y[mask>0]

        print('mask', mask)

        inds = np.arange(len(X_masked))
        X_train, X_test, y_train, y_test, inds_train, inds_test = train_test_split(X_masked, y_masked, inds, random_state=42)

        model_pipeline.fit(X_train, y_train)
        predicted_test = model_pipeline.predict(X_test)
        mae = mean_absolute_error(predicted_test, y_test)
        
        print('mae', mae)
        print(np.hstack([predicted_test, y_test]))
        return ModelCalibrationResult(model_pipeline, mae,
                                      X, y, command_codes,
                                      mask, inds_train, inds_test)
