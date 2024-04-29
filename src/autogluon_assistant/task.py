"""A task encapsulates the data for a data science task or project. It contains descriptions, data, metadata."""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from autogluon.tabular import TabularDataset


class DatasetType(Enum):
    TRAIN = "train"
    TEST = "test"
    OUTPUT = "output"


class TabularPredictionTask:
    """A task contains data and metadata for a tabular machine learning task, including datasets, metadata such as
    problem type, test_id_column, etc.
    """

    preferred_eval_metrics = {
        "binary": "log_loss",
        "multiclass": "log_loss",
        "regression": "root_mean_squared_error",
    }

    def __init__(
        self,
        name: str,
        description: str,
        filepaths: List[Path],
        metadata: Dict[str, Any],
        cache_data: bool = True,
    ):
        self.name = name
        self.description: str = description if description else ""
        self.metadata: Dict[str, Any] = {
            "label_column": None,
            "data_description": "",
            "evaluation_description": "",
            "problem_type": None,
            "eval_metric": None,  # string, keying Autogluon Tabular metrics
            "test_id_column": None,
            **metadata,
        }
        self.filepaths = filepaths
        self.cache_data = cache_data

        self.dataset_mapping: Dict[Union[str, DatasetType], Union[Path, pd.DataFrame, TabularDataset]] = {
            DatasetType.TRAIN: None,
            DatasetType.TEST: None,
            DatasetType.OUTPUT: None,
        }

    def __repr__(self) -> str:
        return f"TabularPredictionTask(name={self.name}, description={self.description[:100]}, {len(self.dataset_mapping)} datasets)"

    def describe(self) -> Dict[str, Any]:
        """Return a description of the task."""
        return {
            "name": self.name,
            "description": self.description,
            "metadata": self.metadata,
            "train_data": self.train_data.describe().to_dict(),
            "test_data": self.test_data.describe().to_dict(),
            "output_data": self.output_data.describe().to_dict(),
        }

    def get_filenames(self) -> List[str]:
        """Return all filenames for the task."""
        return [f.name for f in self.filepaths]

    def _set_task_files(
        self, dataset_name_mapping: Dict[DatasetType, Union[str, Path, pd.DataFrame, TabularDataset]]
    ) -> None:
        """Set the task files for the task."""
        for k, v in dataset_name_mapping.items():
            if isinstance(v, (pd.DataFrame, TabularDataset)):
                self.dataset_mapping[k] = v
            elif isinstance(v, Path):
                self.dataset_mapping[k] = TabularDataset(str(v)) if self.cache_data else v
            elif isinstance(v, str):
                filepath = next(
                    iter([path for path in self.filepaths if path.name == v]), self.filepaths[0].parent / v
                )
                if not filepath.is_file():
                    raise ValueError(f"File {v} not found in task {self.name}")
                self.dataset_mapping[k] = TabularDataset(str(filepath)) if self.cache_data else filepath
            else:
                raise TypeError(f"Unsupported type for dataset_mapping: {type(v)}")

    @property
    def train_data(self) -> TabularDataset:
        return self.load_task_data(DatasetType.TRAIN)

    @train_data.setter
    def train_data(self, data: Union[str, Path, pd.DataFrame, TabularDataset]) -> None:
        self._set_task_files({DatasetType.TRAIN: data})

    @property
    def test_data(self) -> TabularDataset:
        """Return the test dataset for the task."""
        return self.load_task_data(DatasetType.TEST)

    @test_data.setter
    def test_data(self, data: Union[str, Path, pd.DataFrame, TabularDataset]) -> None:
        self._set_task_files({DatasetType.TEST: data})

    @property
    def output_data(self) -> TabularDataset:
        """Return the output dataset for the task."""
        return self.load_task_data(DatasetType.OUTPUT)

    @output_data.setter
    def output_data(self, data: Union[str, Path, pd.DataFrame, TabularDataset]) -> None:
        if self.output_data is not None:
            raise ValueError("Output data already set for task")
        self._set_task_files({DatasetType.OUTPUT: data})

    @property
    def output_columns(self) -> List[str]:
        """Return the output dataset columns for the task."""
        return self.output_data.columns.to_list()

    @property
    def label_column(self) -> Optional[str]:
        """Return the label column for the task."""
        return self.metadata.get("label_column", self.output_columns[-1])

    @property
    def columns_in_train_but_not_test(self) -> List[str]:
        return list(set(self.train_data.columns) - set(self.test_data.columns))

    @property
    def data_description(self) -> str:
        return self.metadata.get("data_description", self.description)

    @property
    def evaluation_description(self) -> str:
        return self.metadata.get("evaluation_description", self.description)

    @property
    def test_id_column(self) -> Optional[str]:
        return self.metadata.get("test_id_column", self.test_data.columns[0])

    @property
    def output_id_column(self) -> Optional[str]:
        return self.metadata.get(
            "output_id_column", self.output_data.columns[0] if self.output_data is not None else None
        )

    def _find_problem_type_in_description(self) -> Optional[str]:
        """Find the problem type in the task description."""
        if "regression" in self.description.lower():
            return "regression"
        elif "classification" in self.description.lower():
            return "binary"
        else:
            return None

    @property
    def problem_type(self) -> Optional[str]:
        return self.metadata["problem_type"] or self._find_problem_type_in_description()

    @property
    def eval_metric(self) -> Optional[str]:
        return self.metadata["eval_metric"] or (
            self.preferred_eval_metrics[self.problem_type] if self.problem_type else None
        )

    def load_task_data(self, dataset_key: Union[str, DatasetType]) -> TabularDataset:
        """Load the competition file for the task."""
        if dataset_key not in self.dataset_mapping:
            raise ValueError(f"Dataset type {dataset_key} not found for task {self.name}")

        dataset = self.dataset_mapping[dataset_key]
        if dataset is None:
            return None
        if isinstance(dataset, pd.DataFrame):
            return TabularDataset(dataset)
        elif isinstance(dataset, TabularDataset):
            return dataset
        else:
            filename = dataset.name
            if filename.split(".")[-1] == ".json":
                raise TypeError(f"File {filename} has unsupported type: json")

            return TabularDataset(str(dataset))