#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级船舶油耗预测模型
Advanced Ship Fuel Consumption Prediction Model

专门针对"XX船舶在XX平均速度下的重油mt预测"进行优化
基于航运行业属性、租约条款、船舶档案特征建立的高精度预测模型

特色功能：
1. 多算法集成预测 (Random Forest, XGBoost, LightGBM)
2. 船舶类型专用模型
3. 速度区间自适应预测
4. 租约条款智能分析
5. 实时预测API

作者: 船舶油耗预测系统
日期: 2025-09-21
"""

import pandas as pd
import numpy as np
import joblib
import warnings
from typing import Dict, List, Tuple, Optional, Any
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
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

class AdvancedFuelPredictor:
    """高级船舶油耗预测器"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_columns = []
        self.ship_type_models = {}
        self.is_trained = False
        
        # 船舶类型特定参数
        self.ship_type_params = {
            'Bulk Carrier': {'base_consumption': 22.5, 'speed_factor': 1.2},
            'Container Ship': {'base_consumption': 28.0, 'speed_factor': 1.4},
            'Crude Oil Tanker': {'base_consumption': 25.8, 'speed_factor': 1.1},
            'Chemical Tanker': {'base_consumption': 24.2, 'speed_factor': 1.15},
            'General Cargo': {'base_consumption': 23.5, 'speed_factor': 1.25},
            'Open Hatch Cargo': {'base_consumption': 24.8, 'speed_factor': 1.18},
            'Other': {'base_consumption': 25.0, 'speed_factor': 1.2}
        }
        
        # 速度区间参数
        self.speed_ranges = {
            'low': (0, 8),      # 低速
            'medium': (8, 15),  # 中速
            'high': (15, 25)    # 高速
        }
    
    def load_processed_data(self, data_path: str) -> pd.DataFrame:
        """加载处理后的数据"""
        print("📂 加载处理后的数据...")
        df = pd.read_csv(data_path)
        print(f"数据行数: {len(df)}")
        return df
    
    def prepare_training_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """准备训练数据"""
        print("📋 准备训练数据...")
        
        # 特征列
        feature_columns = [
            # 基础船舶特征
            '平均速度(kts)', '航行距离(nm)', '航行时间(hrs)',
            '船舶载重(t)', '船舶吃水(m)', '船舶总长度(m)',
            
            # 工程化特征
            '船舶效率系数', '载重状态系数',
            '单位距离油耗', '单位时间油耗', '载重吨油耗比',
            '综合效率指标', '理论速度差异',
            
            # 租约特征
            '重油CP_标准化', '轻油CP_标准化', '航速CP_标准化',
            
            # 位置特征
            '纬度', '经度',
            
            # 分类特征编码
            '船舶类型_标准化_编码', '载重吨位等级_编码', 
            '船龄分组_编码', '载重状态_填充_编码', '航行区域_编码'
        ]
        
        # 检查特征是否存在
        available_features = [col for col in feature_columns if col in df.columns]
        missing_features = [col for col in feature_columns if col not in df.columns]
        
        if missing_features:
            print(f"⚠️ 缺失特征: {missing_features}")
        
        self.feature_columns = available_features
        
        # 准备特征矩阵
        X = df[self.feature_columns].values
        y = df['重油IFO(mt)'].values
        
        # 处理缺失值和异常值
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        
        # 进一步清理异常值
        X = np.clip(X, -1e6, 1e6)  # 限制数值范围
        
        print(f"特征数量: {len(self.feature_columns)}")
        print(f"样本数量: {len(X)}")
        
        return X, y, self.feature_columns
    
    def train_ensemble_models(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """训练集成模型"""
        print("\n🤖 训练集成预测模型...")
        
        # 数据分割
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # 特征标准化
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        self.scalers['main'] = scaler
        
        models = {}
        results = {}
        
        # 1. Random Forest
        print("  训练 Random Forest...")
        rf_params = {
            'n_estimators': 200,
            'max_depth': 15,
            'min_samples_split': 5,
            'min_samples_leaf': 2,
            'random_state': 42,
            'n_jobs': -1
        }
        
        rf_model = RandomForestRegressor(**rf_params)
        rf_model.fit(X_train, y_train)
        rf_pred = rf_model.predict(X_test)
        
        models['random_forest'] = rf_model
        results['random_forest'] = self._evaluate_model(y_test, rf_pred)
        
        # 2. XGBoost (如果可用)
        if XGBOOST_AVAILABLE:
            print("  训练 XGBoost...")
            xgb_params = {
                'n_estimators': 200,
                'max_depth': 8,
                'learning_rate': 0.1,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'random_state': 42,
                'n_jobs': -1
            }
            
            xgb_model = xgb.XGBRegressor(**xgb_params)
            xgb_model.fit(X_train_scaled, y_train)
            xgb_pred = xgb_model.predict(X_test_scaled)
            
            models['xgboost'] = xgb_model
            results['xgboost'] = self._evaluate_model(y_test, xgb_pred)
        
        # 3. LightGBM (如果可用)
        if LIGHTGBM_AVAILABLE:
            print("  训练 LightGBM...")
            lgb_params = {
                'n_estimators': 200,
                'max_depth': 8,
                'learning_rate': 0.1,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'random_state': 42,
                'n_jobs': -1,
                'verbose': -1
            }
            
            lgb_model = lgb.LGBMRegressor(**lgb_params)
            lgb_model.fit(X_train_scaled, y_train)
            lgb_pred = lgb_model.predict(X_test_scaled)
            
            models['lightgbm'] = lgb_model
            results['lightgbm'] = self._evaluate_model(y_test, lgb_pred)
        
        # 集成预测
        ensemble_pred = self._ensemble_predict(models, X_test, X_test_scaled)
        results['ensemble'] = self._evaluate_model(y_test, ensemble_pred)
        
        self.models = models
        
        # 显示结果
        self._display_results(results)
        
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
    
    def _ensemble_predict(self, models: Dict, X: np.ndarray, X_scaled: np.ndarray) -> np.ndarray:
        """集成预测"""
        predictions = []
        weights = []
        
        # Random Forest
        if 'random_forest' in models:
            pred = models['random_forest'].predict(X)
            predictions.append(pred)
            weights.append(0.4)  # RF权重
        
        # XGBoost
        if 'xgboost' in models:
            pred = models['xgboost'].predict(X_scaled)
            predictions.append(pred)
            weights.append(0.35)  # XGB权重
        
        # LightGBM
        if 'lightgbm' in models:
            pred = models['lightgbm'].predict(X_scaled)
            predictions.append(pred)
            weights.append(0.25)  # LGB权重
        
        # 加权平均
        if len(predictions) > 1:
            # 归一化权重
            weights = np.array(weights[:len(predictions)])
            weights = weights / weights.sum()
            
            ensemble_pred = np.average(predictions, axis=0, weights=weights)
        else:
            ensemble_pred = predictions[0]
        
        return ensemble_pred
    
    def _display_results(self, results: Dict):
        """显示训练结果"""
        print("\n📊 模型性能对比:")
        print("-" * 70)
        print(f"{'模型':<15} {'MAE':<8} {'RMSE':<8} {'R²':<8} {'MAPE(%)':<10}")
        print("-" * 70)
        
        for model_name, metrics in results.items():
            print(f"{model_name:<15} {metrics['MAE']:<8.2f} {metrics['RMSE']:<8.2f} "
                  f"{metrics['R2']:<8.3f} {metrics['MAPE']:<10.2f}")
        
        print("-" * 70)
    
    def train_ship_specific_models(self, df: pd.DataFrame):
        """训练船舶类型专用模型"""
        print("\n🚢 训练船舶类型专用模型...")
        
        ship_types = df['船舶类型_标准化'].unique()
        
        for ship_type in ship_types:
            if pd.isna(ship_type):
                continue
                
            ship_data = df[df['船舶类型_标准化'] == ship_type]
            
            if len(ship_data) < 100:  # 样本太少跳过
                continue
            
            print(f"  训练 {ship_type} 专用模型 (样本数: {len(ship_data)})")
            
            # 准备数据
            X_ship = ship_data[self.feature_columns].values
            y_ship = ship_data['重油IFO(mt)'].values
            
            X_ship = np.nan_to_num(X_ship, nan=0.0)
            
            if len(X_ship) > 50:  # 确保有足够样本
                # 训练简化的Random Forest模型
                model = RandomForestRegressor(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    n_jobs=-1
                )
                model.fit(X_ship, y_ship)
                self.ship_type_models[ship_type] = model
        
        print(f"完成 {len(self.ship_type_models)} 个船舶专用模型训练")
    
    def predict_fuel_consumption(self, ship_type: str, speed: float, 
                               dwt: float = None, load_condition: str = 'Laden',
                               **kwargs) -> Dict:
        """
        预测船舶油耗
        
        Args:
            ship_type: 船舶类型
            speed: 平均速度 (kts)
            dwt: 载重吨 (可选)
            load_condition: 载重状态
            **kwargs: 其他特征参数
        
        Returns:
            预测结果字典
        """
        try:
            # 构建特征向量
            features = self._build_feature_vector(
                ship_type, speed, dwt, load_condition, **kwargs
            )
            
            # 集成预测
            ensemble_pred = self._predict_with_ensemble(features)
            
            # 船舶专用模型预测
            ship_specific_pred = self._predict_with_ship_model(
                ship_type, features
            )
            
            # 基于规则的预测 (作为备选)
            rule_based_pred = self._predict_with_rules(
                ship_type, speed, dwt, load_condition
            )
            
            # 综合预测 (加权平均)
            if ship_specific_pred is not None:
                final_pred = 0.6 * ensemble_pred + 0.4 * ship_specific_pred
                confidence = 'High'
            else:
                final_pred = 0.8 * ensemble_pred + 0.2 * rule_based_pred
                confidence = 'Medium'
            
            # 合理性检查
            final_pred = max(5.0, min(100.0, final_pred))
            
            return {
                'predicted_consumption': round(final_pred, 2),
                'confidence': confidence,
                'ship_type': ship_type,
                'speed': speed,
                'ensemble_prediction': round(ensemble_pred, 2),
                'ship_specific_prediction': round(ship_specific_pred, 2) if ship_specific_pred else None,
                'rule_based_prediction': round(rule_based_pred, 2),
                'prediction_range': (
                    round(final_pred * 0.9, 2),
                    round(final_pred * 1.1, 2)
                )
            }
            
        except Exception as e:
            print(f"预测出错: {e}")
            # 返回基于规则的预测作为备选
            rule_pred = self._predict_with_rules(ship_type, speed, dwt, load_condition)
            return {
                'predicted_consumption': round(rule_pred, 2),
                'confidence': 'Low',
                'ship_type': ship_type,
                'speed': speed,
                'error': str(e)
            }
    
    def _build_feature_vector(self, ship_type: str, speed: float, 
                            dwt: float, load_condition: str, **kwargs) -> np.ndarray:
        """构建特征向量"""
        # 默认值
        defaults = {
            '航行距离(nm)': speed * 24,  # 假设24小时航行
            '航行时间(hrs)': 24.0,
            '船舶载重(t)': dwt or 50000,
            '船舶吃水(m)': 8.0,
            '船舶总长度(m)': 150.0,
            '纬度': 0.0,
            '经度': 100.0
        }
        
        # 更新默认值
        defaults.update(kwargs)
        
        # 构建特征向量
        features = np.zeros(len(self.feature_columns))
        
        for i, col in enumerate(self.feature_columns):
            if col == '平均速度(kts)':
                features[i] = speed
            elif col in defaults:
                features[i] = defaults[col]
            elif col.endswith('_编码'):
                # 处理编码特征
                features[i] = self._get_encoded_value(col, ship_type, load_condition)
            else:
                # 计算工程特征
                features[i] = self._calculate_engineered_feature(
                    col, ship_type, speed, defaults
                )
        
        return features.reshape(1, -1)
    
    def _get_encoded_value(self, col: str, ship_type: str, load_condition: str) -> float:
        """获取编码值"""
        if '船舶类型' in col:
            type_mapping = {
                'Bulk Carrier': 0, 'Container Ship': 1, 'Crude Oil Tanker': 2,
                'Chemical Tanker': 3, 'General Cargo': 4, 'Open Hatch Cargo': 5, 'Other': 6
            }
            return type_mapping.get(ship_type, 6)
        elif '载重状态' in col:
            condition_mapping = {'Laden': 0, 'Ballast': 1, 'None': 2}
            return condition_mapping.get(load_condition, 2)
        else:
            return 0.0
    
    def _calculate_engineered_feature(self, col: str, ship_type: str, 
                                    speed: float, defaults: Dict) -> float:
        """计算工程特征"""
        if col == '船舶效率系数':
            efficiency_factors = {
                'Bulk Carrier': 1.0, 'Container Ship': 1.15, 'Crude Oil Tanker': 0.95,
                'Chemical Tanker': 1.05, 'General Cargo': 1.10, 'Open Hatch Cargo': 1.08, 'Other': 1.12
            }
            return efficiency_factors.get(ship_type, 1.0)
        elif col == '载重状态系数':
            return 1.0  # 默认满载状态
        elif col == '单位距离油耗':
            return 25.0 / defaults.get('航行距离(nm)', 240)
        elif col == '单位时间油耗':
            return 25.0 / 24.0
        elif col == '载重吨油耗比':
            return 25.0 / defaults.get('船舶载重(t)', 50000) * 1000
        elif col == '综合效率指标':
            return 1.0 * 1.0 * speed / 10
        elif col == '理论速度差异':
            return speed - speed  # 0差异
        else:
            return defaults.get(col.replace('CP_标准化', 'cp'), 0.0)
    
    def _predict_with_ensemble(self, features: np.ndarray) -> float:
        """使用集成模型预测"""
        if not self.models:
            return 25.0  # 默认值
        
        predictions = []
        weights = []
        
        # Random Forest
        if 'random_forest' in self.models:
            pred = self.models['random_forest'].predict(features)[0]
            predictions.append(pred)
            weights.append(0.4)
        
        # XGBoost
        if 'xgboost' in self.models and 'main' in self.scalers:
            features_scaled = self.scalers['main'].transform(features)
            pred = self.models['xgboost'].predict(features_scaled)[0]
            predictions.append(pred)
            weights.append(0.35)
        
        # LightGBM
        if 'lightgbm' in self.models and 'main' in self.scalers:
            features_scaled = self.scalers['main'].transform(features)
            pred = self.models['lightgbm'].predict(features_scaled)[0]
            predictions.append(pred)
            weights.append(0.25)
        
        if predictions:
            weights = np.array(weights[:len(predictions)])
            weights = weights / weights.sum()
            return np.average(predictions, weights=weights)
        else:
            return 25.0
    
    def _predict_with_ship_model(self, ship_type: str, features: np.ndarray) -> Optional[float]:
        """使用船舶专用模型预测"""
        if ship_type in self.ship_type_models:
            return self.ship_type_models[ship_type].predict(features)[0]
        return None
    
    def _predict_with_rules(self, ship_type: str, speed: float, 
                          dwt: float, load_condition: str) -> float:
        """基于规则的预测"""
        params = self.ship_type_params.get(ship_type, self.ship_type_params['Other'])
        
        base_consumption = params['base_consumption']
        speed_factor = params['speed_factor']
        
        # 速度影响
        speed_effect = (speed / 12) ** speed_factor
        
        # 载重影响
        if dwt:
            dwt_effect = (dwt / 50000) ** 0.3
        else:
            dwt_effect = 1.0
        
        # 载重状态影响
        load_effect = 1.0 if load_condition == 'Laden' else 0.85
        
        predicted_consumption = base_consumption * speed_effect * dwt_effect * load_effect
        
        return predicted_consumption
    
    def save_models(self, model_dir: str = "models"):
        """保存训练好的模型"""
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存主要模型
        model_path = os.path.join(model_dir, f"advanced_fuel_models_{timestamp}.pkl")
        model_data = {
            'models': self.models,
            'scalers': self.scalers,
            'feature_columns': self.feature_columns,
            'ship_type_models': self.ship_type_models,
            'ship_type_params': self.ship_type_params,
            'is_trained': True
        }
        
        joblib.dump(model_data, model_path)
        print(f"✅ 模型已保存到: {model_path}")
        
        return model_path
    
    def load_models(self, model_path: str) -> bool:
        """加载训练好的模型"""
        try:
            model_data = joblib.load(model_path)
            
            self.models = model_data['models']
            self.scalers = model_data['scalers']
            self.feature_columns = model_data['feature_columns']
            self.ship_type_models = model_data['ship_type_models']
            self.ship_type_params = model_data.get('ship_type_params', self.ship_type_params)
            self.is_trained = model_data.get('is_trained', True)
            
            print(f"✅ 模型加载成功: {model_path}")
            return True
            
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            return False
    
    def generate_prediction_report(self, ship_type: str, speed_range: Tuple[float, float],
                                 dwt: float = None) -> pd.DataFrame:
        """生成预测报告"""
        print(f"\n📋 生成 {ship_type} 预测报告...")
        
        speeds = np.arange(speed_range[0], speed_range[1] + 0.5, 0.5)
        results = []
        
        for speed in speeds:
            pred_result = self.predict_fuel_consumption(
                ship_type=ship_type,
                speed=speed,
                dwt=dwt,
                load_condition='Laden'
            )
            
            results.append({
                '船舶类型': ship_type,
                '速度(kts)': speed,
                '预测油耗(mt)': pred_result['predicted_consumption'],
                '置信度': pred_result['confidence'],
                '预测范围_下限': pred_result['prediction_range'][0],
                '预测范围_上限': pred_result['prediction_range'][1]
            })
        
        report_df = pd.DataFrame(results)
        return report_df

def main():
    """主函数 - 训练和测试高级预测模型"""
    print("🚀 启动高级船舶油耗预测模型训练...")
    
    predictor = AdvancedFuelPredictor()
    
    try:
        # 1. 加载处理后的数据
        df = predictor.load_processed_data("data/processed_noon_data.csv")
        
        # 2. 准备训练数据
        X, y, feature_columns = predictor.prepare_training_data(df)
        
        # 3. 训练集成模型
        results = predictor.train_ensemble_models(X, y)
        
        # 4. 训练船舶专用模型
        predictor.train_ship_specific_models(df)
        
        # 5. 保存模型
        model_path = predictor.save_models()
        
        # 6. 测试预测功能
        print("\n🧪 测试预测功能...")
        
        test_cases = [
            {'ship_type': 'Bulk Carrier', 'speed': 12.0, 'dwt': 75000},
            {'ship_type': 'Container Ship', 'speed': 18.0, 'dwt': 120000},
            {'ship_type': 'Crude Oil Tanker', 'speed': 14.0, 'dwt': 200000}
        ]
        
        for case in test_cases:
            result = predictor.predict_fuel_consumption(**case)
            print(f"  {case['ship_type']} @ {case['speed']}kts: "
                  f"{result['predicted_consumption']}mt (置信度: {result['confidence']})")
        
        # 7. 生成预测报告
        report = predictor.generate_prediction_report(
            ship_type='Bulk Carrier',
            speed_range=(8, 20),
            dwt=75000
        )
        
        report_path = "outputs/bulk_carrier_prediction_report.csv"
        report.to_csv(report_path, index=False)
        print(f"\n✅ 预测报告已保存到: {report_path}")
        
        print(f"\n🎉 高级预测模型训练完成！")
        print(f"📊 最佳模型性能: R² = {max([r['R2'] for r in results.values()]):.3f}")
        
        return predictor
        
    except Exception as e:
        print(f"❌ 训练过程出错: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()
