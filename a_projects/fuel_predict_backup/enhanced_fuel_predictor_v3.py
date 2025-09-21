#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版船舶油耗预测模型 V3.0
Enhanced Ship Fuel Consumption Prediction Model V3.0

基于相关性分析优化的预测模型，支持更多输入条件：
- 船舶类型 (ship_type)
- 航行速度 (speed) 
- 载重吨 (dwt)
- 船龄 (ship_age)
- 载重状态 (load_condition)
- 船舶尺寸 (draft, length)
- 地理位置 (latitude, longitude)
- 租约条款 (charter_party_terms)

作者: 船舶油耗预测系统
日期: 2025-09-21
版本: 3.0
"""

import pandas as pd
import numpy as np
import joblib
import warnings
from typing import Dict, List, Tuple, Optional, Any
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest, f_regression
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os

# 尝试导入高级算法库
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

warnings.filterwarnings('ignore')

class EnhancedFuelPredictorV3:
    """增强版船舶油耗预测器 V3.0"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_selector = None
        self.selected_features = []
        self.feature_importance = {}
        self.is_trained = False
        
        # 基于相关性分析的特征重要性权重
        self.feature_weights = {
            '重油CP_标准化': 0.7003,
            '船舶总长度(m)': 0.5594,
            '船舶载重(t)': 0.5586,
            '航速CP_标准化': 0.3020,
            '平均速度(kts)': 0.2700,
            '航行距离(nm)': 0.2669,
            '轻油CP_标准化': 0.2496,
            '综合效率指标': 0.2449,
            '船舶吃水(m)': 0.2388,
            '船舶效率系数': 0.1585,
            '纬度': 0.1406,
            '经度': 0.0413,
            '载重状态系数': 0.0326,
            '航行时间(hrs)': 0.0284,
            '船龄_数值': 0.0119
        }
        
        # 船舶类型映射和参数
        self.ship_type_mapping = {
            'bulk carrier': 'Bulk Carrier',
            'bulk': 'Bulk Carrier',
            'container ship': 'Container Ship',
            'container': 'Container Ship',
            'crude oil tanker': 'Crude Oil Tanker',
            'crude tanker': 'Crude Oil Tanker',
            'oil tanker': 'Crude Oil Tanker',
            'chemical tanker': 'Chemical Tanker',
            'product tanker': 'Chemical Tanker',
            'general cargo': 'General Cargo',
            'cargo ship': 'General Cargo',
            'open hatch': 'Open Hatch Cargo',
            'open hatch cargo': 'Open Hatch Cargo'
        }
        
        # 基于分析结果的船舶类型油耗基准
        self.ship_type_baselines = {
            'Container Ship': 13.28,
            'General Cargo': 16.74,
            'Chemical Tanker': 18.41,
            'Other': 18.56,
            'Bulk Carrier': 23.31,
            'Open Hatch Cargo': 25.20,
            'Crude Oil Tanker': 27.85
        }
        
        # 载重状态影响系数
        self.load_condition_factors = {
            'Laden': 1.0,      # 满载
            'Ballast': 0.986,  # 压载 (22.83/23.16)
            'None': 0.99
        }
        
        # 船龄影响系数 (基于分析结果)
        self.ship_age_factors = {
            '新船': 0.967,      # 22.40/23.16
            '中等船龄': 1.007,   # 23.33/23.16
            '老船': 0.996,      # 23.06/23.16
            '高龄船': 0.993     # 22.98/23.16
        }
        
        # 载重吨位等级影响系数
        self.dwt_class_factors = {
            '小型': 0.590,      # 13.67/23.16
            '中型': 0.825,      # 19.11/23.16
            '大型': 1.026,      # 23.77/23.16
            '超大型': 1.336,    # 30.94/23.16
            '巨型': 1.450       # 33.59/23.16
        }
    
    def load_and_prepare_data(self, data_path: str) -> pd.DataFrame:
        """加载和准备训练数据"""
        print("📂 加载训练数据...")
        df = pd.read_csv(data_path)
        print(f"数据行数: {len(df)}")
        
        # 基于相关性选择最重要的特征
        self.selected_features = self._select_important_features(df)
        
        return df
    
    def _select_important_features(self, df: pd.DataFrame) -> List[str]:
        """基于相关性和重要性选择特征"""
        print("\n🔍 基于相关性选择重要特征...")
        
        # 高相关性特征 (>0.2)
        high_corr_features = [
            '平均速度(kts)', '航行距离(nm)', '船舶载重(t)', 
            '船舶吃水(m)', '船舶总长度(m)', '船龄_数值',
            '船舶效率系数', '载重状态系数', '综合效率指标',
            '重油CP_标准化', '轻油CP_标准化', '航速CP_标准化',
            '纬度', '经度'
        ]
        
        # 重要分类特征编码
        categorical_features = [
            '船舶类型_标准化_编码', '载重吨位等级_编码', 
            '船龄分组_编码', '载重状态_填充_编码', '航行区域_编码'
        ]
        
        # 合并所有重要特征
        selected_features = []
        for feature in high_corr_features + categorical_features:
            if feature in df.columns:
                selected_features.append(feature)
        
        print(f"选择的特征数量: {len(selected_features)}")
        print("主要特征:", selected_features[:10])
        
        return selected_features
    
    def train_optimized_model(self, df: pd.DataFrame) -> Dict:
        """训练优化后的模型"""
        print("\n🤖 训练优化模型...")
        
        # 准备特征和目标
        X = df[self.selected_features].values
        y = df['重油IFO(mt)'].values
        
        # 处理缺失值和异常值
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        X = np.clip(X, -1e6, 1e6)
        
        # 数据分割
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=None
        )
        
        # 特征标准化
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        self.scalers['main'] = scaler
        
        # 特征选择
        selector = SelectKBest(score_func=f_regression, k=15)
        X_train_selected = selector.fit_transform(X_train_scaled, y_train)
        X_test_selected = selector.transform(X_test_scaled)
        self.feature_selector = selector
        
        # 获取选择的特征名
        selected_indices = selector.get_support(indices=True)
        self.selected_feature_names = [self.selected_features[i] for i in selected_indices]
        
        print(f"最终选择的特征数量: {len(self.selected_feature_names)}")
        
        models = {}
        results = {}
        
        # 1. Random Forest (基础模型)
        print("  训练 Random Forest...")
        rf_model = RandomForestRegressor(
            n_estimators=300,
            max_depth=20,
            min_samples_split=3,
            min_samples_leaf=1,
            random_state=42,
            n_jobs=-1
        )
        rf_model.fit(X_train_selected, y_train)
        rf_pred = rf_model.predict(X_test_selected)
        
        models['random_forest'] = rf_model
        results['random_forest'] = self._evaluate_model(y_test, rf_pred)
        
        # 获取特征重要性
        self.feature_importance['random_forest'] = dict(
            zip(self.selected_feature_names, rf_model.feature_importances_)
        )
        
        # 2. XGBoost (如果可用)
        if XGBOOST_AVAILABLE:
            print("  训练 XGBoost...")
            xgb_model = xgb.XGBRegressor(
                n_estimators=300,
                max_depth=10,
                learning_rate=0.08,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1
            )
            xgb_model.fit(X_train_selected, y_train)
            xgb_pred = xgb_model.predict(X_test_selected)
            
            models['xgboost'] = xgb_model
            results['xgboost'] = self._evaluate_model(y_test, xgb_pred)
            
            # 特征重要性
            self.feature_importance['xgboost'] = dict(
                zip(self.selected_feature_names, xgb_model.feature_importances_)
            )
        
        # 3. LightGBM (如果可用)
        if LIGHTGBM_AVAILABLE:
            print("  训练 LightGBM...")
            lgb_model = lgb.LGBMRegressor(
                n_estimators=300,
                max_depth=10,
                learning_rate=0.08,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
                verbose=-1
            )
            lgb_model.fit(X_train_selected, y_train)
            lgb_pred = lgb_model.predict(X_test_selected)
            
            models['lightgbm'] = lgb_model
            results['lightgbm'] = self._evaluate_model(y_test, lgb_pred)
            
            # 特征重要性
            self.feature_importance['lightgbm'] = dict(
                zip(self.selected_feature_names, lgb_model.feature_importances_)
            )
        
        # 集成预测
        ensemble_pred = self._ensemble_predict(models, X_test_selected)
        results['ensemble'] = self._evaluate_model(y_test, ensemble_pred)
        
        self.models = models
        self.is_trained = True
        
        # 显示结果
        self._display_results(results)
        self._display_feature_importance()
        
        return results
    
    def _evaluate_model(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
        """评估模型性能"""
        mae = mean_absolute_error(y_true, y_pred)
        mse = mean_squared_error(y_true, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_true, y_pred)
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        
        return {
            'MAE': mae,
            'MSE': mse,
            'RMSE': rmse,
            'R2': r2,
            'MAPE': mape
        }
    
    def _ensemble_predict(self, models: Dict, X: np.ndarray) -> np.ndarray:
        """集成预测"""
        predictions = []
        weights = []
        
        if 'random_forest' in models:
            predictions.append(models['random_forest'].predict(X))
            weights.append(0.4)
        
        if 'xgboost' in models:
            predictions.append(models['xgboost'].predict(X))
            weights.append(0.35)
        
        if 'lightgbm' in models:
            predictions.append(models['lightgbm'].predict(X))
            weights.append(0.25)
        
        if len(predictions) > 1:
            weights = np.array(weights[:len(predictions)])
            weights = weights / weights.sum()
            return np.average(predictions, axis=0, weights=weights)
        else:
            return predictions[0]
    
    def _display_results(self, results: Dict):
        """显示训练结果"""
        print("\n📊 优化模型性能对比:")
        print("-" * 70)
        print(f"{'模型':<15} {'MAE':<8} {'RMSE':<8} {'R²':<8} {'MAPE(%)':<10}")
        print("-" * 70)
        
        for model_name, metrics in results.items():
            print(f"{model_name:<15} {metrics['MAE']:<8.3f} {metrics['RMSE']:<8.3f} "
                  f"{metrics['R2']:<8.4f} {metrics['MAPE']:<10.2f}")
        
        print("-" * 70)
    
    def _display_feature_importance(self):
        """显示特征重要性"""
        if not self.feature_importance:
            return
        
        print("\n🔍 特征重要性分析:")
        print("-" * 50)
        
        # 计算平均重要性
        avg_importance = {}
        for feature in self.selected_feature_names:
            importances = []
            for model_name, importance_dict in self.feature_importance.items():
                if feature in importance_dict:
                    importances.append(importance_dict[feature])
            
            if importances:
                avg_importance[feature] = np.mean(importances)
        
        # 按重要性排序
        sorted_importance = sorted(avg_importance.items(), key=lambda x: x[1], reverse=True)
        
        print(f"{'特征名称':<25} {'平均重要性':<12}")
        print("-" * 40)
        for feature, importance in sorted_importance[:10]:
            print(f"{feature:<25} {importance:<12.4f}")
    
    def predict_with_enhanced_features(self, ship_type: str, speed: float, 
                                     dwt: float = None, ship_age: float = None,
                                     load_condition: str = 'Laden',
                                     draft: float = None, length: float = None,
                                     latitude: float = None, longitude: float = None,
                                     heavy_fuel_cp: float = None, 
                                     light_fuel_cp: float = None,
                                     speed_cp: float = None) -> Dict:
        """
        使用增强特征进行预测
        
        Args:
            ship_type: 船舶类型
            speed: 航行速度 (kts)
            dwt: 载重吨 (可选)
            ship_age: 船龄 (年) (可选)
            load_condition: 载重状态 ('Laden', 'Ballast')
            draft: 船舶吃水 (m) (可选)
            length: 船舶总长度 (m) (可选)
            latitude: 纬度 (可选)
            longitude: 经度 (可选)
            heavy_fuel_cp: 重油CP (可选)
            light_fuel_cp: 轻油CP (可选)
            speed_cp: 航速CP (可选)
        
        Returns:
            预测结果字典
        """
        try:
            # 标准化船舶类型
            ship_type_normalized = self._normalize_ship_type(ship_type)
            
            # 构建特征向量
            features = self._build_enhanced_feature_vector(
                ship_type_normalized, speed, dwt, ship_age, load_condition,
                draft, length, latitude, longitude, heavy_fuel_cp, 
                light_fuel_cp, speed_cp
            )
            
            if self.is_trained and self.models:
                # 使用训练好的模型预测
                prediction = self._predict_with_trained_model(features)
                confidence = 'High'
                method = 'ml_model'
            else:
                # 使用增强的基于规则的预测
                prediction = self._predict_with_enhanced_rules(
                    ship_type_normalized, speed, dwt, ship_age, 
                    load_condition, draft, length
                )
                confidence = 'Medium'
                method = 'enhanced_rules'
            
            # 合理性检查
            prediction = max(5.0, min(100.0, prediction))
            
            return {
                'predicted_consumption': round(prediction, 2),
                'confidence': confidence,
                'method': method,
                'ship_type': ship_type_normalized,
                'speed': speed,
                'input_features': {
                    'dwt': dwt,
                    'ship_age': ship_age,
                    'load_condition': load_condition,
                    'draft': draft,
                    'length': length,
                    'coordinates': (latitude, longitude) if latitude and longitude else None
                },
                'prediction_range': (
                    round(prediction * 0.9, 2),
                    round(prediction * 1.1, 2)
                ),
                'prediction_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'ship_type': ship_type,
                'speed': speed,
                'status': 'failed'
            }
    
    def _build_enhanced_feature_vector(self, ship_type: str, speed: float,
                                     dwt: float, ship_age: float, load_condition: str,
                                     draft: float, length: float, latitude: float,
                                     longitude: float, heavy_fuel_cp: float,
                                     light_fuel_cp: float, speed_cp: float) -> np.ndarray:
        """构建增强特征向量"""
        # 设置默认值
        dwt = dwt or self._estimate_dwt_from_ship_type(ship_type)
        draft = draft or self._estimate_draft_from_dwt(dwt)
        length = length or self._estimate_length_from_dwt(dwt)
        ship_age = ship_age or 10.0  # 默认10年
        latitude = latitude or 0.0
        longitude = longitude or 100.0
        heavy_fuel_cp = heavy_fuel_cp or 600.0  # 默认重油价格
        light_fuel_cp = light_fuel_cp or 800.0  # 默认轻油价格
        speed_cp = speed_cp or speed  # 默认航速CP等于实际航速
        
        # 构建特征字典
        feature_dict = {}
        
        # 基础特征
        feature_dict['平均速度(kts)'] = speed
        feature_dict['航行距离(nm)'] = speed * 24  # 假设24小时航行
        feature_dict['船舶载重(t)'] = dwt
        feature_dict['船舶吃水(m)'] = draft
        feature_dict['船舶总长度(m)'] = length
        feature_dict['船龄_数值'] = ship_age
        feature_dict['纬度'] = latitude
        feature_dict['经度'] = longitude
        
        # 租约特征
        feature_dict['重油CP_标准化'] = heavy_fuel_cp
        feature_dict['轻油CP_标准化'] = light_fuel_cp
        feature_dict['航速CP_标准化'] = speed_cp
        
        # 工程特征
        feature_dict['船舶效率系数'] = self._get_ship_efficiency_factor(ship_type)
        feature_dict['载重状态系数'] = self.load_condition_factors.get(load_condition, 1.0)
        feature_dict['综合效率指标'] = (
            feature_dict['船舶效率系数'] * 
            feature_dict['载重状态系数'] * 
            speed / 10
        )
        
        # 分类特征编码
        feature_dict['船舶类型_标准化_编码'] = self._encode_ship_type(ship_type)
        feature_dict['载重吨位等级_编码'] = self._encode_dwt_class(dwt)
        feature_dict['船龄分组_编码'] = self._encode_age_group(ship_age)
        feature_dict['载重状态_填充_编码'] = self._encode_load_condition(load_condition)
        feature_dict['航行区域_编码'] = self._encode_region(latitude, longitude)
        
        # 转换为特征向量
        features = []
        for feature_name in self.selected_features:
            if feature_name in feature_dict:
                features.append(feature_dict[feature_name])
            else:
                features.append(0.0)
        
        return np.array(features).reshape(1, -1)
    
    def _predict_with_trained_model(self, features: np.ndarray) -> float:
        """使用训练好的模型预测"""
        # 标准化特征
        if 'main' in self.scalers:
            features_scaled = self.scalers['main'].transform(features)
        else:
            features_scaled = features
        
        # 特征选择
        if self.feature_selector:
            features_selected = self.feature_selector.transform(features_scaled)
        else:
            features_selected = features_scaled
        
        # 集成预测
        predictions = []
        weights = []
        
        if 'random_forest' in self.models:
            pred = self.models['random_forest'].predict(features_selected)[0]
            predictions.append(pred)
            weights.append(0.4)
        
        if 'xgboost' in self.models:
            pred = self.models['xgboost'].predict(features_selected)[0]
            predictions.append(pred)
            weights.append(0.35)
        
        if 'lightgbm' in self.models:
            pred = self.models['lightgbm'].predict(features_selected)[0]
            predictions.append(pred)
            weights.append(0.25)
        
        if predictions:
            weights = np.array(weights[:len(predictions)])
            weights = weights / weights.sum()
            return np.average(predictions, weights=weights)
        else:
            return 25.0
    
    def _predict_with_enhanced_rules(self, ship_type: str, speed: float,
                                   dwt: float, ship_age: float,
                                   load_condition: str, draft: float,
                                   length: float) -> float:
        """使用增强规则预测"""
        # 基础油耗 (基于船舶类型)
        base_consumption = self.ship_type_baselines.get(ship_type, 23.0)
        
        # 速度影响 (非线性关系)
        speed_factor = (speed / 12) ** 1.8
        
        # 载重吨影响
        if dwt:
            dwt_class = self._classify_dwt(dwt)
            dwt_factor = self.dwt_class_factors.get(dwt_class, 1.0)
        else:
            dwt_factor = 1.0
        
        # 船龄影响
        if ship_age:
            age_group = self._classify_age(ship_age)
            age_factor = self.ship_age_factors.get(age_group, 1.0)
        else:
            age_factor = 1.0
        
        # 载重状态影响
        load_factor = self.load_condition_factors.get(load_condition, 1.0)
        
        # 船舶尺寸影响 (基于吃水和长度)
        size_factor = 1.0
        if draft and length:
            # 较大的船舶通常更高效
            size_factor = 0.95 + (draft / 15) * 0.1 + (length / 200) * 0.05
            size_factor = min(1.15, max(0.85, size_factor))
        
        # 综合预测
        predicted_consumption = (
            base_consumption * 
            speed_factor * 
            dwt_factor * 
            age_factor * 
            load_factor * 
            size_factor
        )
        
        return predicted_consumption
    
    def _normalize_ship_type(self, ship_type: str) -> str:
        """标准化船舶类型"""
        return self.ship_type_mapping.get(ship_type.lower(), ship_type)
    
    def _estimate_dwt_from_ship_type(self, ship_type: str) -> float:
        """根据船舶类型估算载重吨"""
        typical_dwt = {
            'Bulk Carrier': 75000,
            'Container Ship': 120000,
            'Crude Oil Tanker': 200000,
            'Chemical Tanker': 45000,
            'General Cargo': 25000,
            'Open Hatch Cargo': 35000,
            'Other': 50000
        }
        return typical_dwt.get(ship_type, 50000)
    
    def _estimate_draft_from_dwt(self, dwt: float) -> float:
        """根据载重吨估算吃水"""
        return 8.0 + (dwt / 100000) * 6.0  # 经验公式
    
    def _estimate_length_from_dwt(self, dwt: float) -> float:
        """根据载重吨估算船长"""
        return 150.0 + (dwt / 50000) * 50.0  # 经验公式
    
    def _get_ship_efficiency_factor(self, ship_type: str) -> float:
        """获取船舶效率系数"""
        efficiency_factors = {
            'Bulk Carrier': 1.0,
            'Container Ship': 1.15,
            'Crude Oil Tanker': 0.95,
            'Chemical Tanker': 1.05,
            'General Cargo': 1.10,
            'Open Hatch Cargo': 1.08,
            'Other': 1.12
        }
        return efficiency_factors.get(ship_type, 1.0)
    
    def _classify_dwt(self, dwt: float) -> str:
        """分类载重吨位"""
        if dwt < 20000:
            return '小型'
        elif dwt < 50000:
            return '中型'
        elif dwt < 100000:
            return '大型'
        elif dwt < 200000:
            return '超大型'
        else:
            return '巨型'
    
    def _classify_age(self, age: float) -> str:
        """分类船龄"""
        if age < 5:
            return '新船'
        elif age < 10:
            return '中等船龄'
        elif age < 20:
            return '老船'
        else:
            return '高龄船'
    
    def _encode_ship_type(self, ship_type: str) -> float:
        """编码船舶类型"""
        type_mapping = {
            'Bulk Carrier': 0, 'Container Ship': 1, 'Crude Oil Tanker': 2,
            'Chemical Tanker': 3, 'General Cargo': 4, 'Open Hatch Cargo': 5, 'Other': 6
        }
        return type_mapping.get(ship_type, 6)
    
    def _encode_dwt_class(self, dwt: float) -> float:
        """编码载重吨位等级"""
        dwt_class = self._classify_dwt(dwt)
        class_mapping = {'小型': 0, '中型': 1, '大型': 2, '超大型': 3, '巨型': 4}
        return class_mapping.get(dwt_class, 2)
    
    def _encode_age_group(self, age: float) -> float:
        """编码船龄分组"""
        age_group = self._classify_age(age)
        age_mapping = {'新船': 0, '中等船龄': 1, '老船': 2, '高龄船': 3}
        return age_mapping.get(age_group, 1)
    
    def _encode_load_condition(self, load_condition: str) -> float:
        """编码载重状态"""
        condition_mapping = {'Laden': 0, 'Ballast': 1, 'None': 2}
        return condition_mapping.get(load_condition, 0)
    
    def _encode_region(self, latitude: float, longitude: float) -> float:
        """编码航行区域"""
        if latitude is None or longitude is None:
            return 0
        
        # 简化的区域编码
        if -10 <= latitude <= 30 and 30 <= longitude <= 120:
            return 2  # 印度洋
        elif 0 <= latitude <= 50 and 100 <= longitude <= 180:
            return 4  # 西太平洋
        elif 30 <= latitude <= 70 and -30 <= longitude <= 50:
            return 1  # 北大西洋
        elif -40 <= latitude <= 0 and -70 <= longitude <= 20:
            return 3  # 南大西洋
        else:
            return 0  # 其他区域
    
    def save_model(self, model_dir: str = "models") -> str:
        """保存模型"""
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = os.path.join(model_dir, f"enhanced_fuel_model_v3_{timestamp}.pkl")
        
        model_data = {
            'models': self.models,
            'scalers': self.scalers,
            'feature_selector': self.feature_selector,
            'selected_features': self.selected_features,
            'selected_feature_names': getattr(self, 'selected_feature_names', []),
            'feature_importance': self.feature_importance,
            'ship_type_baselines': self.ship_type_baselines,
            'load_condition_factors': self.load_condition_factors,
            'ship_age_factors': self.ship_age_factors,
            'dwt_class_factors': self.dwt_class_factors,
            'is_trained': self.is_trained,
            'version': '3.0'
        }
        
        joblib.dump(model_data, model_path)
        print(f"✅ 模型V3已保存到: {model_path}")
        
        return model_path
    
    def load_model(self, model_path: str) -> bool:
        """加载模型"""
        try:
            model_data = joblib.load(model_path)
            
            self.models = model_data['models']
            self.scalers = model_data['scalers']
            self.feature_selector = model_data['feature_selector']
            self.selected_features = model_data['selected_features']
            self.selected_feature_names = model_data.get('selected_feature_names', [])
            self.feature_importance = model_data['feature_importance']
            self.ship_type_baselines = model_data.get('ship_type_baselines', self.ship_type_baselines)
            self.load_condition_factors = model_data.get('load_condition_factors', self.load_condition_factors)
            self.ship_age_factors = model_data.get('ship_age_factors', self.ship_age_factors)
            self.dwt_class_factors = model_data.get('dwt_class_factors', self.dwt_class_factors)
            self.is_trained = model_data.get('is_trained', True)
            
            print(f"✅ 模型V3加载成功: {model_path}")
            return True
            
        except Exception as e:
            print(f"❌ 模型V3加载失败: {e}")
            return False

def main():
    """主函数 - 训练和测试增强模型V3"""
    print("🚀 启动增强版船舶油耗预测模型V3训练...")
    
    predictor = EnhancedFuelPredictorV3()
    
    try:
        # 1. 加载和准备数据
        df = predictor.load_and_prepare_data("data/processed_noon_data.csv")
        
        # 2. 训练优化模型
        results = predictor.train_optimized_model(df)
        
        # 3. 保存模型
        model_path = predictor.save_model()
        
        # 4. 测试增强预测功能
        print("\n🧪 测试增强预测功能...")
        
        test_cases = [
            {
                'ship_type': 'Bulk Carrier',
                'speed': 12.0,
                'dwt': 75000,
                'ship_age': 8,
                'load_condition': 'Laden',
                'draft': 12.5,
                'length': 225
            },
            {
                'ship_type': 'Container Ship',
                'speed': 18.0,
                'dwt': 120000,
                'ship_age': 5,
                'load_condition': 'Laden',
                'latitude': 35.0,
                'longitude': 139.0,
                'heavy_fuel_cp': 650
            },
            {
                'ship_type': 'Crude Oil Tanker',
                'speed': 14.0,
                'dwt': 200000,
                'ship_age': 15,
                'load_condition': 'Ballast'
            }
        ]
        
        for i, case in enumerate(test_cases, 1):
            result = predictor.predict_with_enhanced_features(**case)
            if 'predicted_consumption' in result:
                print(f"  测试{i}: {case['ship_type']} @ {case['speed']}kts")
                print(f"    预测油耗: {result['predicted_consumption']}mt")
                print(f"    置信度: {result['confidence']}")
                print(f"    方法: {result['method']}")
                if 'input_features' in result:
                    features = result['input_features']
                    print(f"    输入特征: DWT={features['dwt']}, 船龄={features['ship_age']}, "
                          f"载重状态={features['load_condition']}")
        
        print(f"\n🎉 增强模型V3训练完成！")
        print(f"📊 最佳性能: R² = {max([r['R2'] for r in results.values()]):.4f}")
        
        return predictor
        
    except Exception as e:
        print(f"❌ 训练过程出错: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()
