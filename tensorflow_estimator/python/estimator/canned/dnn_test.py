# Copyright 2017 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Tests for dnn.py."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import shutil
import tempfile

from absl.testing import parameterized
import numpy as np
import six

from tensorflow.core.example import example_pb2
from tensorflow.core.example import feature_pb2
from tensorflow_estimator.python.estimator.canned import dnn
from tensorflow_estimator.python.estimator.canned import dnn_testing_utils
from tensorflow_estimator.python.estimator.canned import prediction_keys
from tensorflow_estimator.python.estimator.export import export
from tensorflow_estimator.python.estimator.inputs import numpy_io
from tensorflow_estimator.python.estimator.inputs import pandas_io
from tensorflow.python.feature_column import feature_column
from tensorflow.python.feature_column import feature_column_v2
from tensorflow.python.framework import dtypes
from tensorflow.python.framework import ops
from tensorflow.python.ops import data_flow_ops
from tensorflow.python.ops import parsing_ops
from tensorflow.python.platform import gfile
from tensorflow.python.platform import test
from tensorflow.python.summary.writer import writer_cache
from tensorflow.python.training import input as input_lib
from tensorflow.python.training import queue_runner

try:
  # pylint: disable=g-import-not-at-top
  import pandas as pd
  HAS_PANDAS = True
except IOError:
  # Pandas writes a temporary file during import. If it fails, don't use pandas.
  HAS_PANDAS = False
except ImportError:
  HAS_PANDAS = False


def _dnn_classifier_fn(*args, **kwargs):
  return dnn.DNNClassifier(*args, **kwargs)


class DNNModelFnTest(dnn_testing_utils.BaseDNNModelFnTest, test.TestCase):

  def __init__(self, methodName='runTest'):  # pylint: disable=invalid-name
    test.TestCase.__init__(self, methodName)
    dnn_testing_utils.BaseDNNModelFnTest.__init__(
        self, dnn._dnn_model_fn, fc_impl=feature_column)


class DNNModelFnV2Test(dnn_testing_utils.BaseDNNModelFnTest, test.TestCase):

  def __init__(self, methodName='runTest'):  # pylint: disable=invalid-name
    test.TestCase.__init__(self, methodName)
    dnn_testing_utils.BaseDNNModelFnTest.__init__(
        self, dnn._dnn_model_fn, fc_impl=feature_column_v2)


class DNNLogitFnTest(dnn_testing_utils.BaseDNNLogitFnTest, test.TestCase):

  def __init__(self, methodName='runTest'):  # pylint: disable=invalid-name
    test.TestCase.__init__(self, methodName)
    dnn_testing_utils.BaseDNNLogitFnTest.__init__(
        self, dnn._dnn_logit_fn_builder, fc_impl=feature_column)


class DNNLogitFnV2Test(dnn_testing_utils.BaseDNNLogitFnTest, test.TestCase):

  def __init__(self, methodName='runTest'):  # pylint: disable=invalid-name
    test.TestCase.__init__(self, methodName)
    dnn_testing_utils.BaseDNNLogitFnTest.__init__(
        self, dnn._dnn_logit_fn_builder, fc_impl=feature_column_v2)


class DNNWarmStartingTest(dnn_testing_utils.BaseDNNWarmStartingTest,
                          test.TestCase):

  def __init__(self, methodName='runTest'):  # pylint: disable=invalid-name
    test.TestCase.__init__(self, methodName)
    dnn_testing_utils.BaseDNNWarmStartingTest.__init__(
        self, _dnn_classifier_fn, _dnn_regressor_fn, fc_impl=feature_column)


class DNNWarmStartingV2Test(dnn_testing_utils.BaseDNNWarmStartingTest,
                            test.TestCase):

  def __init__(self, methodName='runTest'):  # pylint: disable=invalid-name
    test.TestCase.__init__(self, methodName)
    dnn_testing_utils.BaseDNNWarmStartingTest.__init__(
        self, _dnn_classifier_fn, _dnn_regressor_fn, fc_impl=feature_column_v2)


class DNNClassifierEvaluateTest(
    dnn_testing_utils.BaseDNNClassifierEvaluateTest, test.TestCase):

  def __init__(self, methodName='runTest'):  # pylint: disable=invalid-name
    test.TestCase.__init__(self, methodName)
    dnn_testing_utils.BaseDNNClassifierEvaluateTest.__init__(
        self, _dnn_classifier_fn, fc_impl=feature_column)


class DNNClassifierEvaluateV2Test(
    dnn_testing_utils.BaseDNNClassifierEvaluateTest, test.TestCase):

  def __init__(self, methodName='runTest'):  # pylint: disable=invalid-name
    test.TestCase.__init__(self, methodName)
    dnn_testing_utils.BaseDNNClassifierEvaluateTest.__init__(
        self, _dnn_classifier_fn, fc_impl=feature_column_v2)


class DNNClassifierPredictTest(
    dnn_testing_utils.BaseDNNClassifierPredictTest, test.TestCase):

  def __init__(self, methodName='runTest'):  # pylint: disable=invalid-name
    test.TestCase.__init__(self, methodName)
    dnn_testing_utils.BaseDNNClassifierPredictTest.__init__(
        self, _dnn_classifier_fn, fc_impl=feature_column)


class DNNClassifierPredictV2Test(dnn_testing_utils.BaseDNNClassifierPredictTest,
                                 test.TestCase):

  def __init__(self, methodName='runTest'):  # pylint: disable=invalid-name
    test.TestCase.__init__(self, methodName)
    dnn_testing_utils.BaseDNNClassifierPredictTest.__init__(
        self, _dnn_classifier_fn, fc_impl=feature_column_v2)


class DNNClassifierTrainTest(
    dnn_testing_utils.BaseDNNClassifierTrainTest, test.TestCase):

  def __init__(self, methodName='runTest'):  # pylint: disable=invalid-name
    test.TestCase.__init__(self, methodName)
    dnn_testing_utils.BaseDNNClassifierTrainTest.__init__(
        self, _dnn_classifier_fn, fc_impl=feature_column)


class DNNClassifierTrainV2Test(dnn_testing_utils.BaseDNNClassifierTrainTest,
                               test.TestCase):

  def __init__(self, methodName='runTest'):  # pylint: disable=invalid-name
    test.TestCase.__init__(self, methodName)
    dnn_testing_utils.BaseDNNClassifierTrainTest.__init__(
        self, _dnn_classifier_fn, fc_impl=feature_column_v2)


def _dnn_regressor_fn(*args, **kwargs):
  return dnn.DNNRegressor(*args, **kwargs)


class DNNRegressorEvaluateTest(
    dnn_testing_utils.BaseDNNRegressorEvaluateTest, test.TestCase):

  def __init__(self, methodName='runTest'):  # pylint: disable=invalid-name
    test.TestCase.__init__(self, methodName)
    dnn_testing_utils.BaseDNNRegressorEvaluateTest.__init__(
        self, _dnn_regressor_fn, fc_impl=feature_column)


class DNNRegressorEvaluateV2Test(dnn_testing_utils.BaseDNNRegressorEvaluateTest,
                                 test.TestCase):

  def __init__(self, methodName='runTest'):  # pylint: disable=invalid-name
    test.TestCase.__init__(self, methodName)
    dnn_testing_utils.BaseDNNRegressorEvaluateTest.__init__(
        self, _dnn_regressor_fn, fc_impl=feature_column_v2)


class DNNRegressorPredictTest(
    dnn_testing_utils.BaseDNNRegressorPredictTest, test.TestCase):

  def __init__(self, methodName='runTest'):  # pylint: disable=invalid-name
    test.TestCase.__init__(self, methodName)
    dnn_testing_utils.BaseDNNRegressorPredictTest.__init__(
        self, _dnn_regressor_fn, fc_impl=feature_column)


class DNNRegressorPredictV2Test(dnn_testing_utils.BaseDNNRegressorPredictTest,
                                test.TestCase):

  def __init__(self, methodName='runTest'):  # pylint: disable=invalid-name
    test.TestCase.__init__(self, methodName)
    dnn_testing_utils.BaseDNNRegressorPredictTest.__init__(
        self, _dnn_regressor_fn, fc_impl=feature_column_v2)


class DNNRegressorTrainTest(
    dnn_testing_utils.BaseDNNRegressorTrainTest, test.TestCase):

  def __init__(self, methodName='runTest'):  # pylint: disable=invalid-name
    test.TestCase.__init__(self, methodName)
    dnn_testing_utils.BaseDNNRegressorTrainTest.__init__(
        self, _dnn_regressor_fn, fc_impl=feature_column)


class DNNRegressorTrainV2Test(dnn_testing_utils.BaseDNNRegressorTrainTest,
                              test.TestCase):

  def __init__(self, methodName='runTest'):  # pylint: disable=invalid-name
    test.TestCase.__init__(self, methodName)
    dnn_testing_utils.BaseDNNRegressorTrainTest.__init__(
        self, _dnn_regressor_fn, fc_impl=feature_column_v2)


def _queue_parsed_features(feature_map):
  tensors_to_enqueue = []
  keys = []
  for key, tensor in six.iteritems(feature_map):
    keys.append(key)
    tensors_to_enqueue.append(tensor)
  queue_dtypes = [x.dtype for x in tensors_to_enqueue]
  input_queue = data_flow_ops.FIFOQueue(capacity=100, dtypes=queue_dtypes)
  queue_runner.add_queue_runner(
      queue_runner.QueueRunner(
          input_queue,
          [input_queue.enqueue(tensors_to_enqueue)]))
  dequeued_tensors = input_queue.dequeue()
  return {keys[i]: dequeued_tensors[i] for i in range(len(dequeued_tensors))}


@parameterized.parameters((feature_column,), (feature_column_v2,))
class DNNRegressorIntegrationTest(test.TestCase, parameterized.TestCase):

  def setUp(self):
    self._model_dir = tempfile.mkdtemp()

  def tearDown(self):
    if self._model_dir:
      writer_cache.FileWriterCache.clear()
      shutil.rmtree(self._model_dir)

  def _test_complete_flow(self, train_input_fn, eval_input_fn, predict_input_fn,
                          input_dimension, label_dimension, batch_size,
                          fc_impl):
    feature_columns = [fc_impl.numeric_column('x', shape=(input_dimension,))]

    est = dnn.DNNRegressor(
        hidden_units=(2, 2),
        feature_columns=feature_columns,
        label_dimension=label_dimension,
        model_dir=self._model_dir)

    # TRAIN
    num_steps = 10
    est.train(train_input_fn, steps=num_steps)

    # EVALUTE
    scores = est.evaluate(eval_input_fn)
    self.assertEqual(num_steps, scores[ops.GraphKeys.GLOBAL_STEP])
    self.assertIn('loss', six.iterkeys(scores))

    # PREDICT
    predictions = np.array([
        x[prediction_keys.PredictionKeys.PREDICTIONS]
        for x in est.predict(predict_input_fn)
    ])
    self.assertAllEqual((batch_size, label_dimension), predictions.shape)

    # EXPORT
    feature_spec = fc_impl.make_parse_example_spec(feature_columns)
    serving_input_receiver_fn = export.build_parsing_serving_input_receiver_fn(
        feature_spec)
    export_dir = est.export_savedmodel(tempfile.mkdtemp(),
                                       serving_input_receiver_fn)
    self.assertTrue(gfile.Exists(export_dir))

  def test_numpy_input_fn(self, fc_impl):
    """Tests complete flow with numpy_input_fn."""
    label_dimension = 2
    batch_size = 10
    data = np.linspace(0., 2., batch_size * label_dimension, dtype=np.float32)
    data = data.reshape(batch_size, label_dimension)
    # learn y = x
    train_input_fn = numpy_io.numpy_input_fn(
        x={'x': data},
        y=data,
        batch_size=batch_size,
        num_epochs=None,
        shuffle=True)
    eval_input_fn = numpy_io.numpy_input_fn(
        x={'x': data},
        y=data,
        batch_size=batch_size,
        shuffle=False)
    predict_input_fn = numpy_io.numpy_input_fn(
        x={'x': data},
        batch_size=batch_size,
        shuffle=False)

    self._test_complete_flow(
        train_input_fn=train_input_fn,
        eval_input_fn=eval_input_fn,
        predict_input_fn=predict_input_fn,
        input_dimension=label_dimension,
        label_dimension=label_dimension,
        batch_size=batch_size,
        fc_impl=fc_impl)

  def test_pandas_input_fn(self, fc_impl):
    """Tests complete flow with pandas_input_fn."""
    if not HAS_PANDAS:
      return
    label_dimension = 1
    batch_size = 10
    data = np.linspace(0., 2., batch_size, dtype=np.float32)
    x = pd.DataFrame({'x': data})
    y = pd.Series(data)
    train_input_fn = pandas_io.pandas_input_fn(
        x=x,
        y=y,
        batch_size=batch_size,
        num_epochs=None,
        shuffle=True)
    eval_input_fn = pandas_io.pandas_input_fn(
        x=x,
        y=y,
        batch_size=batch_size,
        shuffle=False)
    predict_input_fn = pandas_io.pandas_input_fn(
        x=x,
        batch_size=batch_size,
        shuffle=False)

    self._test_complete_flow(
        train_input_fn=train_input_fn,
        eval_input_fn=eval_input_fn,
        predict_input_fn=predict_input_fn,
        input_dimension=label_dimension,
        label_dimension=label_dimension,
        batch_size=batch_size,
        fc_impl=fc_impl)

  def test_input_fn_from_parse_example(self, fc_impl):
    """Tests complete flow with input_fn constructed from parse_example."""
    label_dimension = 2
    batch_size = 10
    data = np.linspace(0., 2., batch_size * label_dimension, dtype=np.float32)
    data = data.reshape(batch_size, label_dimension)

    serialized_examples = []
    for datum in data:
      example = example_pb2.Example(features=feature_pb2.Features(
          feature={
              'x': feature_pb2.Feature(
                  float_list=feature_pb2.FloatList(value=datum)),
              'y': feature_pb2.Feature(
                  float_list=feature_pb2.FloatList(value=datum)),
          }))
      serialized_examples.append(example.SerializeToString())

    feature_spec = {
        'x': parsing_ops.FixedLenFeature([label_dimension], dtypes.float32),
        'y': parsing_ops.FixedLenFeature([label_dimension], dtypes.float32),
    }
    def _train_input_fn():
      feature_map = parsing_ops.parse_example(serialized_examples, feature_spec)
      features = _queue_parsed_features(feature_map)
      labels = features.pop('y')
      return features, labels
    def _eval_input_fn():
      feature_map = parsing_ops.parse_example(
          input_lib.limit_epochs(serialized_examples, num_epochs=1),
          feature_spec)
      features = _queue_parsed_features(feature_map)
      labels = features.pop('y')
      return features, labels
    def _predict_input_fn():
      feature_map = parsing_ops.parse_example(
          input_lib.limit_epochs(serialized_examples, num_epochs=1),
          feature_spec)
      features = _queue_parsed_features(feature_map)
      features.pop('y')
      return features, None

    self._test_complete_flow(
        train_input_fn=_train_input_fn,
        eval_input_fn=_eval_input_fn,
        predict_input_fn=_predict_input_fn,
        input_dimension=label_dimension,
        label_dimension=label_dimension,
        batch_size=batch_size,
        fc_impl=fc_impl)


@parameterized.parameters((feature_column,), (feature_column_v2,))
class DNNClassifierIntegrationTest(test.TestCase):

  def setUp(self):
    self._model_dir = tempfile.mkdtemp()

  def tearDown(self):
    if self._model_dir:
      writer_cache.FileWriterCache.clear()
      shutil.rmtree(self._model_dir)

  def _as_label(self, data_in_float):
    return np.rint(data_in_float).astype(np.int64)

  def _test_complete_flow(self, train_input_fn, eval_input_fn, predict_input_fn,
                          input_dimension, n_classes, batch_size, fc_impl):
    feature_columns = [fc_impl.numeric_column('x', shape=(input_dimension,))]

    est = dnn.DNNClassifier(
        hidden_units=(2, 2),
        feature_columns=feature_columns,
        n_classes=n_classes,
        model_dir=self._model_dir)

    # TRAIN
    num_steps = 10
    est.train(train_input_fn, steps=num_steps)

    # EVALUTE
    scores = est.evaluate(eval_input_fn)
    self.assertEqual(num_steps, scores[ops.GraphKeys.GLOBAL_STEP])
    self.assertIn('loss', six.iterkeys(scores))

    # PREDICT
    predicted_proba = np.array([
        x[prediction_keys.PredictionKeys.PROBABILITIES]
        for x in est.predict(predict_input_fn)
    ])
    self.assertAllEqual((batch_size, n_classes), predicted_proba.shape)

    # EXPORT
    feature_spec = fc_impl.make_parse_example_spec(feature_columns)
    serving_input_receiver_fn = export.build_parsing_serving_input_receiver_fn(
        feature_spec)
    export_dir = est.export_savedmodel(tempfile.mkdtemp(),
                                       serving_input_receiver_fn)
    self.assertTrue(gfile.Exists(export_dir))

  def test_numpy_input_fn(self, fc_impl):
    """Tests complete flow with numpy_input_fn."""
    n_classes = 3
    input_dimension = 2
    batch_size = 10
    data = np.linspace(
        0., n_classes - 1., batch_size * input_dimension, dtype=np.float32)
    x_data = data.reshape(batch_size, input_dimension)
    y_data = np.reshape(self._as_label(data[:batch_size]), (batch_size, 1))
    # learn y = x
    train_input_fn = numpy_io.numpy_input_fn(
        x={'x': x_data},
        y=y_data,
        batch_size=batch_size,
        num_epochs=None,
        shuffle=True)
    eval_input_fn = numpy_io.numpy_input_fn(
        x={'x': x_data},
        y=y_data,
        batch_size=batch_size,
        shuffle=False)
    predict_input_fn = numpy_io.numpy_input_fn(
        x={'x': x_data},
        batch_size=batch_size,
        shuffle=False)

    self._test_complete_flow(
        train_input_fn=train_input_fn,
        eval_input_fn=eval_input_fn,
        predict_input_fn=predict_input_fn,
        input_dimension=input_dimension,
        n_classes=n_classes,
        batch_size=batch_size,
        fc_impl=fc_impl)

  def test_pandas_input_fn(self, fc_impl):
    """Tests complete flow with pandas_input_fn."""
    if not HAS_PANDAS:
      return
    input_dimension = 1
    n_classes = 3
    batch_size = 10
    data = np.linspace(0., n_classes - 1., batch_size, dtype=np.float32)
    x = pd.DataFrame({'x': data})
    y = pd.Series(self._as_label(data))
    train_input_fn = pandas_io.pandas_input_fn(
        x=x,
        y=y,
        batch_size=batch_size,
        num_epochs=None,
        shuffle=True)
    eval_input_fn = pandas_io.pandas_input_fn(
        x=x,
        y=y,
        batch_size=batch_size,
        shuffle=False)
    predict_input_fn = pandas_io.pandas_input_fn(
        x=x,
        batch_size=batch_size,
        shuffle=False)

    self._test_complete_flow(
        train_input_fn=train_input_fn,
        eval_input_fn=eval_input_fn,
        predict_input_fn=predict_input_fn,
        input_dimension=input_dimension,
        n_classes=n_classes,
        batch_size=batch_size,
        fc_impl=fc_impl)

  def test_input_fn_from_parse_example(self, fc_impl):
    """Tests complete flow with input_fn constructed from parse_example."""
    input_dimension = 2
    n_classes = 3
    batch_size = 10
    data = np.linspace(
        0., n_classes - 1., batch_size * input_dimension, dtype=np.float32)
    data = data.reshape(batch_size, input_dimension)

    serialized_examples = []
    for datum in data:
      example = example_pb2.Example(features=feature_pb2.Features(
          feature={
              'x':
                  feature_pb2.Feature(float_list=feature_pb2.FloatList(
                      value=datum)),
              'y':
                  feature_pb2.Feature(int64_list=feature_pb2.Int64List(
                      value=self._as_label(datum[:1]))),
          }))
      serialized_examples.append(example.SerializeToString())

    feature_spec = {
        'x': parsing_ops.FixedLenFeature([input_dimension], dtypes.float32),
        'y': parsing_ops.FixedLenFeature([1], dtypes.int64),
    }
    def _train_input_fn():
      feature_map = parsing_ops.parse_example(serialized_examples, feature_spec)
      features = _queue_parsed_features(feature_map)
      labels = features.pop('y')
      return features, labels
    def _eval_input_fn():
      feature_map = parsing_ops.parse_example(
          input_lib.limit_epochs(serialized_examples, num_epochs=1),
          feature_spec)
      features = _queue_parsed_features(feature_map)
      labels = features.pop('y')
      return features, labels
    def _predict_input_fn():
      feature_map = parsing_ops.parse_example(
          input_lib.limit_epochs(serialized_examples, num_epochs=1),
          feature_spec)
      features = _queue_parsed_features(feature_map)
      features.pop('y')
      return features, None

    self._test_complete_flow(
        train_input_fn=_train_input_fn,
        eval_input_fn=_eval_input_fn,
        predict_input_fn=_predict_input_fn,
        input_dimension=input_dimension,
        n_classes=n_classes,
        batch_size=batch_size,
        fc_impl=fc_impl)


if __name__ == '__main__':
  test.main()
