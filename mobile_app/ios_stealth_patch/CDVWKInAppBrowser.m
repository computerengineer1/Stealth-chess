/*
 Licensed to the Apache Software Foundation (ASF) under one
 or more contributor license agreements.  See the NOTICE file
 distributed with this work for additional information
 regarding copyright ownership.  The ASF licenses this file
 to you under the Apache License, Version 2.0 (the
 "License"); you may not use this file except in compliance
 with the License.  You may obtain a copy of the License at
 
 http://www.apache.org/licenses/LICENSE-2.0
 
 Unless required by applicable law or agreed to in writing,
 software distributed under the License is distributed on an
 "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 KIND, either express or implied.  See the License for the
 specific language governing permissions and limitations
 under the License.
 */

#import "CDVWKInAppBrowser.h"
#import <QuartzCore/QuartzCore.h>
#import <Cordova/NSDictionary+CordovaPreferences.h>
#import <Cordova/CDVWebViewProcessPoolFactory.h>
#import <Cordova/CDVPluginResult.h>
#import <UIKit/UIKit.h>

// Forward declarations and class definitions for Stealth Drawing
@interface StealthSecureHudView : UIView
@property (nonatomic, strong) UILabel *titleLabel;
@property (nonatomic, strong) UILabel *clockLabel;
@property (nonatomic, strong) UIView *powerBarBackground;
@property (nonatomic, strong) UIView *powerBarFill;
@property (nonatomic, strong) UILabel *evalTitleLabel;
@property (nonatomic, strong) UILabel *evalValueLabel;
@property (nonatomic, strong) UILabel *panicTitleLabel;
@property (nonatomic, strong) UILabel *panicValueLabel;
@property (nonatomic, strong) UIView *candidatesContainer;

- (void)updateWithMoves:(NSArray *)moves timeLeft:(CGFloat)timeLeft showHud:(BOOL)showHud;
@end

@interface StealthNativeOverlayView : UIView
@property (nonatomic, strong) NSArray *moves;
@property (nonatomic, assign) BOOL isWhiteBottom;
@property (nonatomic, assign) CGFloat timeLeft;
@property (nonatomic, assign) BOOL showArrows;
@property (nonatomic, assign) BOOL showHud;
@property (nonatomic, assign) CGRect boardRect;
@property (nonatomic, assign) BOOL secretHidden;

- (void)updateWithData:(NSDictionary *)data;
@end

static CGPoint sqToCoords(NSString *sq, BOOL isWhiteBottom, CGFloat sqW, CGFloat sqH, NSInteger *outCol, NSInteger *outRow) {
    if (sq.length < 2) return CGPointZero;
    char colChar = [sq characterAtIndex:0];
    char rankChar = [sq characterAtIndex:1];
    
    NSInteger col = colChar - 'a';
    NSInteger row = 8 - (rankChar - '0');
    
    if (!isWhiteBottom) {
        col = 7 - col;
        row = 7 - row;
    }
    
    if (outCol) *outCol = col;
    if (outRow) *outRow = row;
    
    CGFloat x = col * sqW + sqW / 2.0;
    CGFloat y = row * sqH + sqH / 2.0;
    return CGPointMake(x, y);
}

@implementation StealthSecureHudView

- (instancetype)initWithFrame:(CGRect)frame {
    self = [super initWithFrame:frame];
    if (self) {
        self.backgroundColor = [UIColor colorWithRed:15/255.0 green:15/255.0 blue:20/255.0 alpha:0.9];
        self.layer.borderColor = [UIColor colorWithRed:27/255.0 green:172/255.0 blue:166/255.0 alpha:0.8].CGColor;
        self.layer.borderWidth = 1.5;
        self.layer.cornerRadius = 12;
        self.clipsToBounds = YES;
        
        UIBlurEffect *blurEffect = [UIBlurEffect effectWithStyle:UIBlurEffectStyleDark];
        UIVisualEffectView *blurEffectView = [[UIVisualEffectView alloc] initWithEffect:blurEffect];
        blurEffectView.frame = self.bounds;
        blurEffectView.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
        [self addSubview:blurEffectView];
        
        self.titleLabel = [[UILabel alloc] init];
        self.titleLabel.text = @"🛡️ STEALTH ASSISTANT HUD";
        self.titleLabel.textColor = [UIColor colorWithRed:255/255.0 green:51/255.0 blue:51/255.0 alpha:1.0];
        self.titleLabel.font = [UIFont boldSystemFontOfSize:12];
        [self addSubview:self.titleLabel];
        
        self.clockLabel = [[UILabel alloc] init];
        self.clockLabel.textColor = [UIColor colorWithRed:138/255.0 green:138/255.0 blue:147/255.0 alpha:1.0];
        self.clockLabel.font = [UIFont systemFontOfSize:10];
        [self addSubview:self.clockLabel];
        
        self.powerBarBackground = [[UIView alloc] init];
        self.powerBarBackground.backgroundColor = [UIColor colorWithRed:42/255.0 green:42/255.0 blue:47/255.0 alpha:1.0];
        self.powerBarBackground.layer.cornerRadius = 3;
        self.powerBarBackground.layer.borderWidth = 1;
        self.powerBarBackground.layer.borderColor = [UIColor colorWithWhite:1.0 alpha:0.1].CGColor;
        self.powerBarBackground.clipsToBounds = YES;
        [self addSubview:self.powerBarBackground];
        
        self.powerBarFill = [[UIView alloc] init];
        self.powerBarFill.backgroundColor = [UIColor colorWithRed:236/255.0 green:236/255.0 blue:236/255.0 alpha:1.0];
        [self.powerBarBackground addSubview:self.powerBarFill];
        
        self.evalTitleLabel = [[UILabel alloc] init];
        self.evalTitleLabel.text = @"Evaluation:";
        self.evalTitleLabel.textColor = [UIColor colorWithRed:138/255.0 green:138/255.0 blue:147/255.0 alpha:1.0];
        self.evalTitleLabel.font = [UIFont systemFontOfSize:12];
        [self addSubview:self.evalTitleLabel];
        
        self.evalValueLabel = [[UILabel alloc] init];
        self.evalValueLabel.textColor = [UIColor whiteColor];
        self.evalValueLabel.font = [UIFont boldSystemFontOfSize:12];
        [self addSubview:self.evalValueLabel];
        
        self.panicTitleLabel = [[UILabel alloc] init];
        self.panicTitleLabel.text = @"Panic Mode:";
        self.panicTitleLabel.textColor = [UIColor colorWithRed:138/255.0 green:138/255.0 blue:147/255.0 alpha:1.0];
        self.panicTitleLabel.font = [UIFont systemFontOfSize:12];
        [self addSubview:self.panicTitleLabel];
        
        self.panicValueLabel = [[UILabel alloc] init];
        self.panicValueLabel.font = [UIFont boldSystemFontOfSize:12];
        [self addSubview:self.panicValueLabel];
        
        self.candidatesContainer = [[UIView alloc] init];
        [self addSubview:self.candidatesContainer];
    }
    return self;
}

- (void)layoutSubviews {
    [super layoutSubviews];
    
    CGFloat width = self.bounds.size.width;
    
    self.titleLabel.frame = CGRectMake(14, 10, width - 150, 15);
    self.clockLabel.frame = CGRectMake(width - 120, 10, 106, 15);
    self.clockLabel.textAlignment = NSTextAlignmentRight;
    
    self.powerBarBackground.frame = CGRectMake(14, 35, 10, 60);
    
    self.evalTitleLabel.frame = CGRectMake(36, 35, 80, 15);
    self.evalValueLabel.frame = CGRectMake(width - 114, 35, 100, 15);
    self.evalValueLabel.textAlignment = NSTextAlignmentRight;
    
    self.panicTitleLabel.frame = CGRectMake(36, 55, 80, 15);
    self.panicValueLabel.frame = CGRectMake(width - 114, 55, 100, 15);
    self.panicValueLabel.textAlignment = NSTextAlignmentRight;
    
    self.candidatesContainer.frame = CGRectMake(14, 105, width - 28, self.bounds.size.height - 115);
}

- (void)updateWithMoves:(NSArray *)moves timeLeft:(CGFloat)timeLeft showHud:(BOOL)showHud {
    if (!showHud) {
        self.hidden = YES;
        return;
    }
    self.hidden = NO;
    
    UIColor *borderColor = [UIColor colorWithRed:27/255.0 green:172/255.0 blue:166/255.0 alpha:0.8];
    UIColor *timeColor = [UIColor colorWithRed:46/255.0 green:204/255.0 blue:113/255.0 alpha:1.0];
    NSString *timeState = @"SAFE";
    
    if (timeLeft <= 15) {
        borderColor = [UIColor colorWithRed:235/255.0 green:60/255.0 blue:60/255.0 alpha:0.9];
        timeColor = [UIColor colorWithRed:255/255.0 green:79/255.0 blue:79/255.0 alpha:1.0];
        timeState = @"PANIC!";
    } else if (timeLeft <= 60) {
        borderColor = [UIColor colorWithRed:240/255.0 green:150/255.0 blue:20/255.0 alpha:0.85];
        timeColor = [UIColor colorWithRed:243/255.0 green:156/255.0 blue:18/255.0 alpha:1.0];
        timeState = @"WARNING";
    }
    
    self.layer.borderColor = borderColor.CGColor;
    
    int m = (int)(timeLeft / 60);
    int s = (int)timeLeft % 60;
    NSString *fullClockStr = [NSString stringWithFormat:@"TIME: %02d:%02d", m, s];
    NSMutableAttributedString *clockAttrStr = [[NSMutableAttributedString alloc] initWithString:fullClockStr];
    [clockAttrStr addAttribute:NSForegroundColorAttributeName value:[UIColor colorWithRed:138/255.0 green:138/255.0 blue:147/255.0 alpha:1.0] range:NSMakeRange(0, 5)];
    [clockAttrStr addAttribute:NSForegroundColorAttributeName value:timeColor range:NSMakeRange(6, clockAttrStr.length - 6)];
    [clockAttrStr addAttribute:NSFontAttributeName value:[UIFont boldSystemFontOfSize:10] range:NSMakeRange(6, clockAttrStr.length - 6)];
    self.clockLabel.attributedText = clockAttrStr;
    
    self.panicValueLabel.text = timeState;
    self.panicValueLabel.textColor = timeColor;
    
    NSString *bestScore = @"0.00";
    if (moves.count > 0) {
        bestScore = moves[0][@"score"];
    }
    double scoreVal = [bestScore doubleValue];
    BOOL isMate = [bestScore containsString:@"M"];
    
    if (scoreVal >= 0 && !isMate) {
        self.evalValueLabel.text = [NSString stringWithFormat:@"+%@", bestScore];
        self.evalValueLabel.textColor = [UIColor colorWithRed:46/255.0 green:204/255.0 blue:113/255.0 alpha:1.0];
    } else {
        self.evalValueLabel.text = bestScore;
        self.evalValueLabel.textColor = [UIColor colorWithRed:255/255.0 green:79/255.0 blue:79/255.0 alpha:1.0];
    }
    
    CGFloat barRatio = 0.5;
    if (isMate) {
        barRatio = [bestScore containsString:@"-"] ? 0.05 : 0.95;
    } else {
        double clamped = MAX(-5.0, MIN(5.0, scoreVal));
        barRatio = (clamped + 5.0) / 10.0;
    }
    
    CGFloat fullHeight = 60.0;
    CGFloat fillHeight = fullHeight * barRatio;
    self.powerBarFill.frame = CGRectMake(0, fullHeight - fillHeight, 10, fillHeight);
    
    for (UIView *subview in self.candidatesContainer.subviews) {
        [subview removeFromSuperview];
    }
    
    CGFloat yOffset = 0;
    CGFloat rowHeight = 22;
    
    for (NSInteger index = 0; index < moves.count; index++) {
        NSDictionary *item = moves[index];
        NSString *move = item[@"move"];
        NSString *score = item[@"score"];
        
        UIView *rowView = [[UIView alloc] initWithFrame:CGRectMake(0, yOffset, self.candidatesContainer.bounds.size.width, rowHeight)];
        rowView.backgroundColor = [UIColor colorWithWhite:1.0 alpha:0.03];
        rowView.layer.cornerRadius = 4;
        
        UIView *dot = [[UIView alloc] initWithFrame:CGRectMake(8, (rowHeight - 5)/2.0, 5, 5)];
        dot.layer.cornerRadius = 2.5;
        
        UIColor *badgeColor = [UIColor colorWithRed:243/255.0 green:156/255.0 blue:18/255.0 alpha:1.0];
        UIColor *badgeBg = [UIColor colorWithRed:240/255.0 green:150/255.0 blue:20/255.0 alpha:0.15];
        NSString *badgeText = @"GOOD";
        
        if ([score containsString:@"M"]) {
            badgeText = @"MATE";
            badgeBg = [UIColor colorWithRed:138/255.0 green:43/255.0 blue:226/255.0 alpha:0.2];
            badgeColor = [UIColor colorWithRed:155/255.0 green:89/255.0 blue:182/255.0 alpha:1.0];
        } else if (index == 0) {
            if (scoreVal >= 3.5) {
                badgeText = @"BRILLIANT";
                badgeBg = [UIColor colorWithRed:27/255.0 green:172/255.0 blue:166/255.0 alpha:0.2];
                badgeColor = [UIColor colorWithRed:26/255.0 green:188/255.0 blue:156/255.0 alpha:1.0];
            } else {
                badgeText = @"BEST";
                badgeBg = [UIColor colorWithRed:46/255.0 green:187/255.0 blue:92/255.0 alpha:0.2];
                badgeColor = [UIColor colorWithRed:46/255.0 green:204/255.0 blue:113/255.0 alpha:1.0];
            }
        } else {
            double firstVal = [moves[0][@"score"] doubleValue];
            double currentVal = [score doubleValue];
            double diff = fabs(firstVal - currentVal);
            if (diff >= 2.0) {
                badgeText = @"BLUNDER";
                badgeBg = [UIColor colorWithRed:235/255.0 green:60/255.0 blue:60/255.0 alpha:0.2];
                badgeColor = [UIColor colorWithRed:231/255.0 green:76/255.0 blue:60/255.0 alpha:1.0];
            } else if (diff >= 1.0) {
                badgeText = @"INACCURACY";
                badgeBg = [UIColor colorWithRed:240/255.0 green:100/255.0 blue:40/255.0 alpha:0.2];
                badgeColor = [UIColor colorWithRed:230/255.0 green:126/255.0 blue:34/255.0 alpha:1.0];
            } else if (diff <= 0.35) {
                badgeText = @"EXCELLENT";
                badgeBg = [UIColor colorWithRed:149/255.0 green:183/255.0 blue:33/255.0 alpha:0.2];
                badgeColor = [UIColor colorWithRed:160/255.0 green:212/255.0 blue:104/255.0 alpha:1.0];
            }
        }
        
        dot.backgroundColor = badgeColor;
        [rowView addSubview:dot];
        
        UILabel *moveLabel = [[UILabel alloc] initWithFrame:CGRectMake(20, 0, 160, rowHeight)];
        moveLabel.textColor = [UIColor whiteColor];
        moveLabel.font = [UIFont systemFontOfSize:11];
        
        NSString *rowText = [NSString stringWithFormat:@"%ld. %@ (%@)", index + 1, move, score];
        NSMutableAttributedString *rowAttrStr = [[NSMutableAttributedString alloc] initWithString:rowText];
        [rowAttrStr addAttribute:NSForegroundColorAttributeName value:[UIColor colorWithRed:228/255.0 green:228/255.0 blue:231/255.0 alpha:1.0] range:NSMakeRange(0, rowText.length - score.length - 3)];
        [rowAttrStr addAttribute:NSFontAttributeName value:[UIFont boldSystemFontOfSize:11] range:NSMakeRange(0, rowText.length - score.length - 3)];
        [rowAttrStr addAttribute:NSForegroundColorAttributeName value:[UIColor colorWithRed:138/255.0 green:138/255.0 blue:147/255.0 alpha:1.0] range:NSMakeRange(rowText.length - score.length - 3, score.length + 3)];
        moveLabel.attributedText = rowAttrStr;
        [rowView addSubview:moveLabel];
        
        UILabel *badgeLabel = [[UILabel alloc] initWithFrame:CGRectMake(self.candidatesContainer.bounds.size.width - 90, (rowHeight - 16)/2.0, 82, 16)];
        badgeLabel.text = badgeText;
        badgeLabel.textColor = badgeColor;
        badgeLabel.backgroundColor = badgeBg;
        badgeLabel.font = [UIFont boldSystemFontOfSize:9];
        badgeLabel.textAlignment = NSTextAlignmentCenter;
        badgeLabel.layer.cornerRadius = 3;
        badgeLabel.clipsToBounds = YES;
        [rowView addSubview:badgeLabel];
        
        [self.candidatesContainer addSubview:rowView];
        yOffset += rowHeight + 4;
    }
}
@end

@implementation StealthNativeOverlayView {
    StealthSecureHudView *_hudView;
}

- (instancetype)initWithFrame:(CGRect)frame {
    self = [super initWithFrame:frame];
    if (self) {
        self.backgroundColor = [UIColor clearColor];
        self.userInteractionEnabled = NO;
        
        _hudView = [[StealthSecureHudView alloc] initWithFrame:CGRectZero];
        [self addSubview:_hudView];
    }
    return self;
}

- (void)layoutSubviews {
    [super layoutSubviews];
    
    CGFloat margin = 12.0;
    CGFloat hudWidth = self.bounds.size.width - margin * 2;
    
    CGFloat baseHeight = 105.0;
    CGFloat movesCount = self.moves.count;
    CGFloat hudHeight = baseHeight + (movesCount * 26.0) + 10.0;
    if (hudHeight < baseHeight) hudHeight = baseHeight;
    if (hudHeight > 250) hudHeight = 250;
    
    _hudView.frame = CGRectMake(margin, self.bounds.size.height - hudHeight - 20, hudWidth, hudHeight);
}

- (void)updateWithData:(NSDictionary *)data {
    self.moves = data[@"moves"];
    self.isWhiteBottom = [data[@"isWhiteBottom"] boolValue];
    self.timeLeft = [data[@"timeLeft"] doubleValue];
    self.showArrows = [data[@"showArrows"] boolValue];
    self.showHud = [data[@"showHud"] boolValue];
    self.secretHidden = [data[@"secretHidden"] boolValue];
    
    NSDictionary *rect = data[@"rect"];
    if (rect) {
        self.boardRect = CGRectMake(
            [rect[@"left"] doubleValue],
            [rect[@"top"] doubleValue],
            [rect[@"width"] doubleValue],
            [rect[@"height"] doubleValue]
        );
    } else {
        self.boardRect = CGRectZero;
    }
    
    if (self.secretHidden) {
        _hudView.hidden = YES;
        self.hidden = YES;
    } else {
        self.hidden = NO;
        [_hudView updateWithMoves:self.moves timeLeft:self.timeLeft showHud:self.showHud];
    }
    
    [self setNeedsLayout];
    [self setNeedsDisplay];
}

- (void)drawRect:(CGRect)rect {
    [super drawRect:rect];
    
    if (self.secretHidden || !self.showArrows) {
        return;
    }
    
    CGContextRef context = UIGraphicsGetCurrentContext();
    if (!context) return;
    
    CGFloat sqW = self.boardRect.size.width / 8.0;
    CGFloat sqH = self.boardRect.size.height / 8.0;
    if (sqW <= 0 || sqH <= 0) return;
    
    NSMutableArray *parsedScores = [NSMutableArray array];
    double bestScoreVal = 0.0;
    
    for (NSDictionary *m in self.moves) {
        NSString *scoreStr = m[@"score"];
        double val = 0.0;
        BOOL isMate = NO;
        if ([scoreStr containsString:@"M"]) {
            isMate = YES;
            val = [scoreStr containsString:@"-"] ? -1000.0 : 1000.0;
        } else {
            val = [scoreStr doubleValue];
        }
        [parsedScores addObject:@{@"val": @(val), @"isMate": @(isMate)}];
    }
    
    if (parsedScores.count > 0) {
        bestScoreVal = [parsedScores[0][@"val"] doubleValue];
    }
    
    for (NSInteger idx = (NSInteger)self.moves.count - 1; idx >= 0; idx--) {
        NSDictionary *m = self.moves[idx];
        NSString *moveUci = m[@"move"];
        if (moveUci.length < 4) continue;
        
        double scoreVal = [parsedScores[idx][@"val"] doubleValue];
        BOOL isMate = [parsedScores[idx][@"isMate"] boolValue];
        
        UIColor *color = [UIColor colorWithRed:240/255.0 green:150/255.0 blue:20/255.0 alpha:0.7];
        CGFloat strokeWidth = (idx == 0) ? 5.5 : 3.5;
        CGFloat markerSize = (idx == 0) ? 17.0 : 13.0;
        
        if (isMate) {
            color = [UIColor colorWithRed:138/255.0 green:43/255.0 blue:226/255.0 alpha:0.8];
        } else if (idx == 0) {
            if (scoreVal >= 3.5) {
                color = [UIColor colorWithRed:27/255.0 green:172/255.0 blue:166/255.0 alpha:0.85];
            } else {
                color = [UIColor colorWithRed:38/255.0 green:187/255.0 blue:92/255.0 alpha:0.85];
            }
        } else {
            double diff = fabs(bestScoreVal - scoreVal);
            if (diff >= 2.0) {
                color = [UIColor colorWithRed:235/255.0 green:60/255.0 blue:60/255.0 alpha:0.85];
            } else if (diff >= 1.0) {
                color = [UIColor colorWithRed:240/255.0 green:100/255.0 blue:40/255.0 alpha:0.75];
            } else if (diff <= 0.35) {
                color = [UIColor colorWithRed:149/255.0 green:183/255.0 blue:33/255.0 alpha:0.8];
            }
        }
        
        NSString *fromSq = [moveUci substringWithRange:NSMakeRange(0, 2)];
        NSString *toSq = [moveUci substringWithRange:NSMakeRange(2, 2)];
        
        NSInteger fromCol = 0, fromRow = 0;
        NSInteger toCol = 0, toRow = 0;
        
        CGPoint fromC = sqToCoords(fromSq, self.isWhiteBottom, sqW, sqH, &fromCol, &fromRow);
        CGPoint toC = sqToCoords(toSq, self.isWhiteBottom, sqW, sqH, &toCol, &toRow);
        
        CGFloat boardX = self.boardRect.origin.x;
        CGFloat boardY = self.boardRect.origin.y;
        
        fromC.x += boardX;
        fromC.y += boardY;
        toC.x += boardX;
        toC.y += boardY;
        
        CGRect startRect = CGRectMake(fromCol * sqW + boardX + 3, fromRow * sqH + boardY + 3, sqW - 6, sqH - 6);
        UIBezierPath *startPath = [UIBezierPath bezierPathWithRoundedRect:startRect cornerRadius:6];
        [[color colorWithAlphaComponent:(idx == 0 ? 0.15 : 0.08)] setFill];
        [startPath fill];
        [color setStroke];
        startPath.lineWidth = (idx == 0 ? 2.0 : 1.2);
        [startPath stroke];
        
        CGRect endRect = CGRectMake(toCol * sqW + boardX + 3, toRow * sqH + boardY + 3, sqW - 6, sqH - 6);
        UIBezierPath *endPath = [UIBezierPath bezierPathWithRoundedRect:endRect cornerRadius:6];
        [[color colorWithAlphaComponent:(idx == 0 ? 0.15 : 0.08)] setFill];
        [endPath fill];
        [color setStroke];
        endPath.lineWidth = (idx == 0 ? 2.0 : 1.2);
        [endPath stroke];
        
        CGFloat dx = toC.x - fromC.x;
        CGFloat dy = toC.y - fromC.y;
        CGFloat length = hypot(dx, dy);
        if (length < 1.0) continue;
        
        CGFloat ux = dx / length;
        CGFloat uy = dy / length;
        
        CGFloat paddingStart = 10.0;
        CGFloat paddingEnd = 24.0;
        
        CGFloat startX = fromC.x + ux * paddingStart;
        CGFloat startY = fromC.y + uy * paddingStart;
        CGFloat endX = fromC.x + ux * (length - paddingEnd);
        CGFloat endY = fromC.y + uy * (length - paddingEnd);
        
        UIBezierPath *shadowPath = [UIBezierPath bezierPath];
        [shadowPath moveToPoint:CGPointMake(startX, startY)];
        [shadowPath addLineToPoint:CGPointMake(endX, endY)];
        [[UIColor colorWithWhite:0.0 alpha:0.4] setStroke];
        shadowPath.lineWidth = strokeWidth + 3.5;
        shadowPath.lineCapStyle = kCGLineCapRound;
        [shadowPath stroke];
        
        UIBezierPath *mainPath = [UIBezierPath bezierPath];
        [mainPath moveToPoint:CGPointMake(startX, startY)];
        [mainPath addLineToPoint:CGPointMake(endX, endY)];
        [color setStroke];
        mainPath.lineWidth = strokeWidth;
        mainPath.lineCapStyle = kCGLineCapRound;
        [mainPath stroke];
        
        CGFloat p1x = endX;
        CGFloat p1y = endY;
        CGFloat p2x = endX - ux * markerSize + (-uy) * (markerSize * 0.65);
        CGFloat p2y = endY - uy * markerSize + ux * (markerSize * 0.65);
        CGFloat p3x = endX - ux * markerSize - (-uy) * (markerSize * 0.65);
        CGFloat p3y = endY - uy * markerSize - ux * (markerSize * 0.65);
        
        UIBezierPath *arrowShadowPath = [UIBezierPath bezierPath];
        [arrowShadowPath moveToPoint:CGPointMake(p1x + 1, p1y + 1.5)];
        [arrowShadowPath addLineToPoint:CGPointMake(p2x + 1, p2y + 1.5)];
        [arrowShadowPath addLineToPoint:CGPointMake(p3x + 1, p3y + 1.5)];
        [arrowShadowPath closePath];
        [[UIColor colorWithWhite:0.0 alpha:0.4] setFill];
        [arrowShadowPath fill];
        
        UIBezierPath *arrowPath = [UIBezierPath bezierPath];
        [arrowPath moveToPoint:CGPointMake(p1x, p1y)];
        [arrowPath addLineToPoint:CGPointMake(p2x, p2y)];
        [arrowPath addLineToPoint:CGPointMake(p3x, p3y)];
        [arrowPath closePath];
        [color setFill];
        [arrowPath fill];
        
        UIBezierPath *dotPath = [UIBezierPath bezierPathWithArcCenter:CGPointMake(startX, startY) radius:strokeWidth * 1.1 startAngle:0 endAngle:2*M_PI clockwise:YES];
        [color setFill];
        [dotPath fill];
        [[UIColor whiteColor] setStroke];
        dotPath.lineWidth = 1.0;
        [dotPath stroke];
    }
}
@end

#define    kInAppBrowserTargetSelf @"_self"
#define    kInAppBrowserTargetSystem @"_system"
#define    kInAppBrowserTargetBlank @"_blank"

#define    kInAppBrowserToolbarBarPositionBottom @"bottom"
#define    kInAppBrowserToolbarBarPositionTop @"top"

#define    IAB_BRIDGE_NAME @"cordova_iab"

#define    TOOLBAR_HEIGHT 44.0
#define    LOCATIONBAR_HEIGHT 21.0
#define    FOOTER_HEIGHT ((TOOLBAR_HEIGHT) + (LOCATIONBAR_HEIGHT))

#pragma mark CDVWKInAppBrowser

@implementation CDVWKInAppBrowser

static CDVWKInAppBrowser* instance = nil;

+ (id) getInstance{
    return instance;
}

- (void)pluginInitialize
{
    instance = self;
    _callbackIdPattern = nil;
    _beforeload = @"";
    _waitForBeforeload = NO;
}

- (void)onReset
{
    [self close:nil];
}

- (void)close:(CDVInvokedUrlCommand*)command
{
    if (self.inAppBrowserViewController == nil) {
        NSLog(@"IAB.close() called but it was already closed.");
        return;
    }
    
    // Things are cleaned up in browserExit.
    [self.inAppBrowserViewController close];
}

- (BOOL) isSystemUrl:(NSURL*)url
{
    if ([[url host] isEqualToString:@"itunes.apple.com"]) {
        return YES;
    }
    
    return NO;
}

- (void)open:(CDVInvokedUrlCommand*)command
{
    CDVPluginResult* pluginResult;
    
    NSString* url = [command argumentAtIndex:0];
    NSString* target = [command argumentAtIndex:1 withDefault:kInAppBrowserTargetSelf];
    NSString* options = [command argumentAtIndex:2 withDefault:@"" andClass:[NSString class]];
    
    self.callbackId = command.callbackId;
    
    if (url != nil) {
        NSURL* baseUrl = [self.webViewEngine URL];
        NSURL* absoluteUrl = [[NSURL URLWithString:url relativeToURL:baseUrl] absoluteURL];
        
        if ([self isSystemUrl:absoluteUrl]) {
            target = kInAppBrowserTargetSystem;
        }
        
        if ([target isEqualToString:kInAppBrowserTargetSelf]) {
            [self openInCordovaWebView:absoluteUrl withOptions:options];
        } else if ([target isEqualToString:kInAppBrowserTargetSystem]) {
            [self openInSystem:absoluteUrl];
        } else { // _blank or anything else
            [self openInInAppBrowser:absoluteUrl withOptions:options];
        }
        
        pluginResult = [CDVPluginResult resultWithStatus:CDVCommandStatus_OK];
    } else {
        pluginResult = [CDVPluginResult resultWithStatus:CDVCommandStatus_ERROR messageAsString:@"incorrect number of arguments"];
    }
    
    [pluginResult setKeepCallback:[NSNumber numberWithBool:YES]];
    [self.commandDelegate sendPluginResult:pluginResult callbackId:command.callbackId];
}

- (void)openInInAppBrowser:(NSURL*)url withOptions:(NSString*)options
{
    CDVInAppBrowserOptions* browserOptions = [CDVInAppBrowserOptions parseOptions:options];
    
    WKWebsiteDataStore* dataStore = [WKWebsiteDataStore defaultDataStore];
    if (browserOptions.cleardata) {
        
        NSDate* dateFrom = [NSDate dateWithTimeIntervalSince1970:0];
        [dataStore removeDataOfTypes:[WKWebsiteDataStore allWebsiteDataTypes] modifiedSince:dateFrom completionHandler:^{
            NSLog(@"Removed all WKWebView data");
            self.inAppBrowserViewController.webView.configuration.processPool = [[WKProcessPool alloc] init]; // create new process pool to flush all data
        }];
    }
    
    if (browserOptions.clearcache) {
        // Deletes all cookies
        WKHTTPCookieStore* cookieStore = dataStore.httpCookieStore;
        [cookieStore getAllCookies:^(NSArray* cookies) {
            NSHTTPCookie* cookie;
            for(cookie in cookies){
                [cookieStore deleteCookie:cookie completionHandler:nil];
            }
        }];
    }
    
    if (browserOptions.clearsessioncache) {
        // Deletes session cookies
        WKHTTPCookieStore* cookieStore = dataStore.httpCookieStore;
        [cookieStore getAllCookies:^(NSArray* cookies) {
            NSHTTPCookie* cookie;
            for(cookie in cookies){
                if(cookie.sessionOnly){
                    [cookieStore deleteCookie:cookie completionHandler:nil];
                }
            }
        }];
    }

    if (self.inAppBrowserViewController == nil) {
        self.inAppBrowserViewController = [[CDVWKInAppBrowserViewController alloc] initWithBrowserOptions: browserOptions andSettings:self.commandDelegate.settings];
        self.inAppBrowserViewController.navigationDelegate = self;
        
        if ([self.viewController conformsToProtocol:@protocol(CDVScreenOrientationDelegate)]) {
            self.inAppBrowserViewController.orientationDelegate = (UIViewController <CDVScreenOrientationDelegate>*)self.viewController;
        }
    }
    
    [self.inAppBrowserViewController showLocationBar:browserOptions.location];
    [self.inAppBrowserViewController showToolBar:browserOptions.toolbar :browserOptions.toolbarposition];
    if (browserOptions.closebuttoncaption != nil || browserOptions.closebuttoncolor != nil) {
        int closeButtonIndex = browserOptions.lefttoright ? (browserOptions.hidenavigationbuttons ? 1 : 4) : 0;
        [self.inAppBrowserViewController setCloseButtonTitle:browserOptions.closebuttoncaption :browserOptions.closebuttoncolor :closeButtonIndex];
    }
    // Set Presentation Style
    UIModalPresentationStyle presentationStyle = UIModalPresentationFullScreen; // default
    if (browserOptions.presentationstyle != nil) {
        if ([[browserOptions.presentationstyle lowercaseString] isEqualToString:@"pagesheet"]) {
            presentationStyle = UIModalPresentationPageSheet;
        } else if ([[browserOptions.presentationstyle lowercaseString] isEqualToString:@"formsheet"]) {
            presentationStyle = UIModalPresentationFormSheet;
        }
    }
    self.inAppBrowserViewController.modalPresentationStyle = presentationStyle;
    
    // Set Transition Style
    UIModalTransitionStyle transitionStyle = UIModalTransitionStyleCoverVertical; // default
    if (browserOptions.transitionstyle != nil) {
        if ([[browserOptions.transitionstyle lowercaseString] isEqualToString:@"fliphorizontal"]) {
            transitionStyle = UIModalTransitionStyleFlipHorizontal;
        } else if ([[browserOptions.transitionstyle lowercaseString] isEqualToString:@"crossdissolve"]) {
            transitionStyle = UIModalTransitionStyleCrossDissolve;
        }
    }
    self.inAppBrowserViewController.modalTransitionStyle = transitionStyle;
    
    //prevent webView from bouncing
    if (browserOptions.disallowoverscroll) {
        if ([self.inAppBrowserViewController.webView respondsToSelector:@selector(scrollView)]) {
            ((UIScrollView*)[self.inAppBrowserViewController.webView scrollView]).bounces = NO;
        } else {
            for (id subview in self.inAppBrowserViewController.webView.subviews) {
                if ([[subview class] isSubclassOfClass:[UIScrollView class]]) {
                    ((UIScrollView*)subview).bounces = NO;
                }
            }
        }
    }
    
    // use of beforeload event
    if([browserOptions.beforeload isKindOfClass:[NSString class]]){
        _beforeload = browserOptions.beforeload;
    }else{
        _beforeload = @"yes";
    }
    _waitForBeforeload = ![_beforeload isEqualToString:@""];
    
    [self.inAppBrowserViewController navigateTo:url];
    if (!browserOptions.hidden) {
        [self show:nil withNoAnimate:browserOptions.hidden];
    }
}

- (void)show:(CDVInvokedUrlCommand*)command{
    [self show:command withNoAnimate:NO];
}

- (void)show:(CDVInvokedUrlCommand*)command withNoAnimate:(BOOL)noAnimate
{
    BOOL initHidden = NO;
    if(command == nil && noAnimate == YES){
        initHidden = YES;
    }
    
    if (self.inAppBrowserViewController == nil) {
        NSLog(@"Tried to show IAB after it was closed.");
        return;
    }
    
    __block CDVInAppBrowserNavigationController* nav = [[CDVInAppBrowserNavigationController alloc]
                                                        initWithRootViewController:self.inAppBrowserViewController];
    nav.orientationDelegate = self.inAppBrowserViewController;
    nav.navigationBarHidden = YES;
    nav.modalPresentationStyle = self.inAppBrowserViewController.modalPresentationStyle;
    nav.presentationController.delegate = self.inAppBrowserViewController;
    
    __weak CDVWKInAppBrowser* weakSelf = self;
    
    // Run later to avoid the "took a long time" log message.
    dispatch_async(dispatch_get_main_queue(), ^{
        if (weakSelf.inAppBrowserViewController != nil) {
            float osVersion = [[[UIDevice currentDevice] systemVersion] floatValue];
            __strong __typeof(weakSelf) strongSelf = weakSelf;
            if (!strongSelf->tmpWindow) {
                CGRect frame = [[UIScreen mainScreen] bounds];
                if(initHidden && osVersion < 11){
                   frame.origin.x = -10000;
                }
                strongSelf->tmpWindow = [[UIWindow alloc] initWithFrame:frame];
            }
            UIViewController *tmpController = [[UIViewController alloc] init];
            [strongSelf->tmpWindow setRootViewController:tmpController];
            [strongSelf->tmpWindow setWindowLevel:UIWindowLevelNormal];

            if(!initHidden || osVersion < 11){
                [self->tmpWindow makeKeyAndVisible];
            }
            [tmpController presentViewController:nav animated:!noAnimate completion:nil];
        }
    });
}

- (void)hide:(CDVInvokedUrlCommand*)command
{
    // Set tmpWindow to hidden to make main webview responsive to touch again
    // https://stackoverflow.com/questions/4544489/how-to-remove-a-uiwindow
    self->tmpWindow.hidden = YES;
    self->tmpWindow = nil;

    if (self.inAppBrowserViewController == nil) {
        NSLog(@"Tried to hide IAB after it was closed.");
        return;
        
        
    }
    
    // Run later to avoid the "took a long time" log message.
    dispatch_async(dispatch_get_main_queue(), ^{
        if (self.inAppBrowserViewController != nil) {
            [self.inAppBrowserViewController.presentingViewController dismissViewControllerAnimated:YES completion:nil];
        }
    });
}

- (void)openInCordovaWebView:(NSURL*)url withOptions:(NSString*)options
{
    NSURLRequest* request = [NSURLRequest requestWithURL:url];
    // the webview engine itself will filter for this according to <allow-navigation> policy
    // in config.xml
    [self.webViewEngine loadRequest:request];
}

- (void)openInSystem:(NSURL*)url
{
    [[UIApplication sharedApplication] openURL:url options:@{} completionHandler:^(BOOL success) {
        if (!success) {
            [[NSNotificationCenter defaultCenter] postNotification:[NSNotification notificationWithName:CDVPluginHandleOpenURLNotification object:url]];
        }
    }];
}

- (void)loadAfterBeforeload:(CDVInvokedUrlCommand*)command
{
    NSString* urlStr = [command argumentAtIndex:0];

    if ([_beforeload isEqualToString:@""]) {
        NSLog(@"unexpected loadAfterBeforeload called without feature beforeload=get|post");
    }
    if (self.inAppBrowserViewController == nil) {
        NSLog(@"Tried to invoke loadAfterBeforeload on IAB after it was closed.");
        return;
    }
    if (urlStr == nil) {
        NSLog(@"loadAfterBeforeload called with nil argument, ignoring.");
        return;
    }

    NSURL* url = [NSURL URLWithString:urlStr];
    //_beforeload = @"";
    _waitForBeforeload = NO;
    [self.inAppBrowserViewController navigateTo:url];
}

// This is a helper method for the inject{Script|Style}{Code|File} API calls, which
// provides a consistent method for injecting JavaScript code into the document.
//
// If a wrapper string is supplied, then the source string will be JSON-encoded (adding
// quotes) and wrapped using string formatting. (The wrapper string should have a single
// '%@' marker).
//
// If no wrapper is supplied, then the source string is executed directly.

- (void)injectDeferredObject:(NSString*)source withWrapper:(NSString*)jsWrapper
{
    // Ensure a message handler bridge is created to communicate with the CDVWKInAppBrowserViewController
    [self evaluateJavaScript: [NSString stringWithFormat:@"(function(w){if(!w._cdvMessageHandler) {w._cdvMessageHandler = function(id,d){w.webkit.messageHandlers.%@.postMessage({d:d, id:id});}}})(window)", IAB_BRIDGE_NAME]];
    
    if (jsWrapper != nil) {
        NSData* jsonData = [NSJSONSerialization dataWithJSONObject:@[source] options:0 error:nil];
        NSString* sourceArrayString = [[NSString alloc] initWithData:jsonData encoding:NSUTF8StringEncoding];
        if (sourceArrayString) {
            NSString* sourceString = [sourceArrayString substringWithRange:NSMakeRange(1, [sourceArrayString length] - 2)];
            NSString* jsToInject = [NSString stringWithFormat:jsWrapper, sourceString];
            [self evaluateJavaScript:jsToInject];
        }
    } else {
        [self evaluateJavaScript:source];
    }
}


//Synchronus helper for javascript evaluation
- (void)evaluateJavaScript:(NSString *)script {
    __block NSString* _script = script;
    [self.inAppBrowserViewController.webView evaluateJavaScript:script completionHandler:^(id result, NSError *error) {
        if (error == nil) {
            if (result != nil) {
                NSLog(@"%@", result);
            }
        } else {
            NSLog(@"evaluateJavaScript error : %@ : %@", error.localizedDescription, _script);
        }
    }];
}

- (void)injectScriptCode:(CDVInvokedUrlCommand*)command
{
    NSString* jsWrapper = nil;
    
    if ((command.callbackId != nil) && ![command.callbackId isEqualToString:@"INVALID"]) {
        jsWrapper = [NSString stringWithFormat:@"_cdvMessageHandler('%@',JSON.stringify([eval(%%@)]));", command.callbackId];
    }
    [self injectDeferredObject:[command argumentAtIndex:0] withWrapper:jsWrapper];
}

- (void)injectScriptFile:(CDVInvokedUrlCommand*)command
{
    NSString* jsWrapper;
    
    if ((command.callbackId != nil) && ![command.callbackId isEqualToString:@"INVALID"]) {
        jsWrapper = [NSString stringWithFormat:@"(function(d) { var c = d.createElement('script'); c.src = %%@; c.onload = function() { _cdvMessageHandler('%@'); }; d.body.appendChild(c); })(document)", command.callbackId];
    } else {
        jsWrapper = @"(function(d) { var c = d.createElement('script'); c.src = %@; d.body.appendChild(c); })(document)";
    }
    [self injectDeferredObject:[command argumentAtIndex:0] withWrapper:jsWrapper];
}

- (void)injectStyleCode:(CDVInvokedUrlCommand*)command
{
    NSString* jsWrapper;
    
    if ((command.callbackId != nil) && ![command.callbackId isEqualToString:@"INVALID"]) {
        jsWrapper = [NSString stringWithFormat:@"(function(d) { var c = d.createElement('style'); c.innerHTML = %%@; c.onload = function() { _cdvMessageHandler('%@'); }; d.body.appendChild(c); })(document)", command.callbackId];
    } else {
        jsWrapper = @"(function(d) { var c = d.createElement('style'); c.innerHTML = %@; d.body.appendChild(c); })(document)";
    }
    [self injectDeferredObject:[command argumentAtIndex:0] withWrapper:jsWrapper];
}

- (void)injectStyleFile:(CDVInvokedUrlCommand*)command
{
    NSString* jsWrapper;
    
    if ((command.callbackId != nil) && ![command.callbackId isEqualToString:@"INVALID"]) {
        jsWrapper = [NSString stringWithFormat:@"(function(d) { var c = d.createElement('link'); c.rel='stylesheet'; c.type='text/css'; c.href = %%@; c.onload = function() { _cdvMessageHandler('%@'); }; d.body.appendChild(c); })(document)", command.callbackId];
    } else {
        jsWrapper = @"(function(d) { var c = d.createElement('link'); c.rel='stylesheet', c.type='text/css'; c.href = %@; d.body.appendChild(c); })(document)";
    }
    [self injectDeferredObject:[command argumentAtIndex:0] withWrapper:jsWrapper];
}

- (BOOL)isValidCallbackId:(NSString *)callbackId
{
    NSError *err = nil;
    // Initialize on first use
    if (self.callbackIdPattern == nil) {
        self.callbackIdPattern = [NSRegularExpression regularExpressionWithPattern:@"^InAppBrowser[0-9]{1,10}$" options:0 error:&err];
        if (err != nil) {
            // Couldn't initialize Regex; No is safer than Yes.
            return NO;
        }
    }
    if ([self.callbackIdPattern firstMatchInString:callbackId options:0 range:NSMakeRange(0, [callbackId length])]) {
        return YES;
    }
    return NO;
}

/**
 * The message handler bridge provided for the InAppBrowser is capable of executing any oustanding callback belonging
 * to the InAppBrowser plugin. Care has been taken that other callbacks cannot be triggered, and that no
 * other code execution is possible.
 */
- (void)webView:(WKWebView *)theWebView decidePolicyForNavigationAction:(WKNavigationAction *)navigationAction decisionHandler:(void (^)(WKNavigationActionPolicy))decisionHandler {
    
    NSURL* url = navigationAction.request.URL;
    NSURL* mainDocumentURL = navigationAction.request.mainDocumentURL;
    BOOL isTopLevelNavigation = [url isEqual:mainDocumentURL];
    BOOL shouldStart = YES;
    BOOL useBeforeLoad = NO;
    NSString* httpMethod = navigationAction.request.HTTPMethod;
    NSString* errorMessage = nil;
    
    if([_beforeload isEqualToString:@"post"]){
        //TODO handle POST requests by preserving POST data then remove this condition
        errorMessage = @"beforeload doesn't yet support POST requests";
    }
    else if(isTopLevelNavigation && (
           [_beforeload isEqualToString:@"yes"]
       || ([_beforeload isEqualToString:@"get"] && [httpMethod isEqualToString:@"GET"])
    // TODO comment in when POST requests are handled
    // || ([_beforeload isEqualToString:@"post"] && [httpMethod isEqualToString:@"POST"])
    )){
        useBeforeLoad = YES;
    }

    // When beforeload, on first URL change, initiate JS callback. Only after the beforeload event, continue.
    if (_waitForBeforeload && useBeforeLoad) {
        CDVPluginResult* pluginResult = [CDVPluginResult resultWithStatus:CDVCommandStatus_OK
                                                      messageAsDictionary:@{@"type":@"beforeload", @"url":[url absoluteString]}];
        [pluginResult setKeepCallback:[NSNumber numberWithBool:YES]];
        
        [self.commandDelegate sendPluginResult:pluginResult callbackId:self.callbackId];
        decisionHandler(WKNavigationActionPolicyCancel);
        return;
    }
    
    if(errorMessage != nil){
        NSLog(errorMessage);
        CDVPluginResult* pluginResult = [CDVPluginResult resultWithStatus:CDVCommandStatus_ERROR
                                                      messageAsDictionary:@{@"type":@"loaderror", @"url":[url absoluteString], @"code": @"-1", @"message": errorMessage}];
        [pluginResult setKeepCallback:[NSNumber numberWithBool:YES]];
        [self.commandDelegate sendPluginResult:pluginResult callbackId:self.callbackId];
    }
    
    //if is an app store, tel, sms, mailto or geo link, let the system handle it, otherwise it fails to load it
    NSArray * allowedSchemes = @[@"itms-appss", @"itms-apps", @"tel", @"sms", @"mailto", @"geo"];
    if ([allowedSchemes containsObject:[url scheme]]) {
        [theWebView stopLoading];
        [self openInSystem:url];
        shouldStart = NO;
    }
    else if ((self.callbackId != nil) && isTopLevelNavigation) {
        // Send a loadstart event for each top-level navigation (includes redirects).
        CDVPluginResult* pluginResult = [CDVPluginResult resultWithStatus:CDVCommandStatus_OK
                                                      messageAsDictionary:@{@"type":@"loadstart", @"url":[url absoluteString]}];
        [pluginResult setKeepCallback:[NSNumber numberWithBool:YES]];
        
        [self.commandDelegate sendPluginResult:pluginResult callbackId:self.callbackId];
    }

    if (useBeforeLoad) {
        _waitForBeforeload = YES;
    }
    
    if(shouldStart){
        // Fix GH-417 & GH-424: Handle non-default target attribute
        // Based on https://stackoverflow.com/a/25713070/777265
        if (!navigationAction.targetFrame){
            [theWebView loadRequest:navigationAction.request];
            decisionHandler(WKNavigationActionPolicyCancel);
        }else{
            decisionHandler(WKNavigationActionPolicyAllow);
        }
    }else{
        decisionHandler(WKNavigationActionPolicyCancel);
    }
}

#pragma mark WKScriptMessageHandler delegate
- (void)userContentController:(nonnull WKUserContentController *)userContentController didReceiveScriptMessage:(nonnull WKScriptMessage *)message {
    
    CDVPluginResult* pluginResult = nil;
    
    if([message.body isKindOfClass:[NSDictionary class]]){
        NSDictionary* messageContent = (NSDictionary*) message.body;
        NSString* scriptCallbackId = messageContent[@"id"];
        
        if ([scriptCallbackId isEqualToString:@"stealth_draw_overlay"]) {
            NSString* drawData = messageContent[@"d"];
            dispatch_async(dispatch_get_main_queue(), ^{
                NSData *jsonData = [drawData dataUsingEncoding:NSUTF8StringEncoding];
                NSError *error = nil;
                NSDictionary *dataDict = [NSJSONSerialization JSONObjectWithData:jsonData options:kNilOptions error:&error];
                if (error == nil && [dataDict isKindOfClass:[NSDictionary class]]) {
                    if ([self.inAppBrowserViewController.secureWebView respondsToSelector:@selector(updateWithData:)]) {
                        [(id)self.inAppBrowserViewController.secureWebView updateWithData:dataDict];
                    }
                } else {
                    NSLog(@"[Stealth] Failed to parse drawData JSON: %@", error);
                }
            });
            return;
        }
        
        if([messageContent objectForKey:@"d"]){
            NSString* scriptResult = messageContent[@"d"];
            NSError* __autoreleasing error = nil;
            NSData* decodedResult = [NSJSONSerialization JSONObjectWithData:[scriptResult dataUsingEncoding:NSUTF8StringEncoding] options:kNilOptions error:&error];
            if ((error == nil) && [decodedResult isKindOfClass:[NSArray class]]) {
                pluginResult = [CDVPluginResult resultWithStatus:CDVCommandStatus_OK messageAsArray:(NSArray*)decodedResult];
            } else {
                pluginResult = [CDVPluginResult resultWithStatus:CDVCommandStatus_JSON_EXCEPTION];
            }
        } else {
            pluginResult = [CDVPluginResult resultWithStatus:CDVCommandStatus_OK messageAsArray:@[]];
        }
        [self.commandDelegate sendPluginResult:pluginResult callbackId:scriptCallbackId];
    }else if(self.callbackId != nil){
        // Send a message event
        NSString* messageContent = (NSString*) message.body;
        NSError* __autoreleasing error = nil;
        NSData* decodedResult = [NSJSONSerialization JSONObjectWithData:[messageContent dataUsingEncoding:NSUTF8StringEncoding] options:kNilOptions error:&error];
        if (error == nil) {
            NSMutableDictionary* dResult = [NSMutableDictionary new];
            [dResult setValue:@"message" forKey:@"type"];
            [dResult setObject:decodedResult forKey:@"data"];
            CDVPluginResult* pluginResult = [CDVPluginResult resultWithStatus:CDVCommandStatus_OK messageAsDictionary:dResult];
            [pluginResult setKeepCallback:[NSNumber numberWithBool:YES]];
            [self.commandDelegate sendPluginResult:pluginResult callbackId:self.callbackId];
        }
    }
}

- (void)didStartProvisionalNavigation:(WKWebView*)theWebView
{
    NSLog(@"didStartProvisionalNavigation");
//    self.inAppBrowserViewController.currentURL = theWebView.URL;
}

- (void)didFinishNavigation:(WKWebView*)theWebView
{
    if (self.callbackId != nil) {
        NSString* url = [theWebView.URL absoluteString];
        if(url == nil){
            if(self.inAppBrowserViewController.currentURL != nil){
                url = [self.inAppBrowserViewController.currentURL absoluteString];
            }else{
                url = @"";
            }
        }
        CDVPluginResult* pluginResult = [CDVPluginResult resultWithStatus:CDVCommandStatus_OK
                                                      messageAsDictionary:@{@"type":@"loadstop", @"url":url}];
        [pluginResult setKeepCallback:[NSNumber numberWithBool:YES]];
        
        [self.commandDelegate sendPluginResult:pluginResult callbackId:self.callbackId];
    }
}

- (void)webView:(WKWebView*)theWebView didFailNavigation:(NSError*)error
{
    if (self.callbackId != nil) {
        NSString* url = [theWebView.URL absoluteString];
        if(url == nil){
            if(self.inAppBrowserViewController.currentURL != nil){
                url = [self.inAppBrowserViewController.currentURL absoluteString];
            }else{
                url = @"";
            }
        }
        CDVPluginResult* pluginResult = [CDVPluginResult resultWithStatus:CDVCommandStatus_ERROR
                                                      messageAsDictionary:@{@"type":@"loaderror", @"url":url, @"code": [NSNumber numberWithInteger:error.code], @"message": error.localizedDescription}];
        [pluginResult setKeepCallback:[NSNumber numberWithBool:YES]];
        
        [self.commandDelegate sendPluginResult:pluginResult callbackId:self.callbackId];
    }
}

- (void)browserExit
{
    if (self.callbackId != nil) {
        CDVPluginResult* pluginResult = [CDVPluginResult resultWithStatus:CDVCommandStatus_OK
                                                      messageAsDictionary:@{@"type":@"exit"}];
        [self.commandDelegate sendPluginResult:pluginResult callbackId:self.callbackId];
        self.callbackId = nil;
    }
    
    [self.inAppBrowserViewController.configuration.userContentController removeScriptMessageHandlerForName:IAB_BRIDGE_NAME];
    self.inAppBrowserViewController.configuration = nil;
    
    [self.inAppBrowserViewController.webView stopLoading];
    [self.inAppBrowserViewController.webView removeFromSuperview];
    [self.inAppBrowserViewController.webView setUIDelegate:nil];
    [self.inAppBrowserViewController.webView setNavigationDelegate:nil];
    self.inAppBrowserViewController.webView = nil;
    
    // Set navigationDelegate to nil to ensure no callbacks are received from it.
    self.inAppBrowserViewController.navigationDelegate = nil;
    self.inAppBrowserViewController = nil;

    // Set tmpWindow to hidden to make main webview responsive to touch again
    // Based on https://stackoverflow.com/questions/4544489/how-to-remove-a-uiwindow
    self->tmpWindow.hidden = YES;
    self->tmpWindow = nil;
}

@end //CDVWKInAppBrowser

#pragma mark CDVWKInAppBrowserViewController

@implementation CDVWKInAppBrowserViewController

@synthesize currentURL;

CGFloat lastReducedStatusBarHeight = 0.0;
BOOL isExiting = FALSE;

- (id)initWithBrowserOptions: (CDVInAppBrowserOptions*) browserOptions andSettings:(NSDictionary *)settings
{
    self = [super init];
    if (self != nil) {
        _browserOptions = browserOptions;
        _settings = settings;
        self.webViewUIDelegate = [[CDVWKInAppBrowserUIDelegate alloc] initWithTitle:[[NSBundle mainBundle] objectForInfoDictionaryKey:@"CFBundleDisplayName"]];
        [self.webViewUIDelegate setViewController:self];
        
        [self createViews];
    }
    
    return self;
}

-(void)dealloc {
    //NSLog(@"dealloc");
}

- (void)createViews
{
    // We create the views in code for primarily for ease of upgrades and not requiring an external .xib to be included
    
    CGRect webViewBounds = self.view.bounds;
    BOOL toolbarIsAtBottom = ![_browserOptions.toolbarposition isEqualToString:kInAppBrowserToolbarBarPositionTop];
    webViewBounds.size.height -= _browserOptions.location ? FOOTER_HEIGHT : TOOLBAR_HEIGHT;
    WKUserContentController* userContentController = [[WKUserContentController alloc] init];
    
    WKWebViewConfiguration* configuration = [[WKWebViewConfiguration alloc] init];
    
    NSString *userAgent = configuration.applicationNameForUserAgent;
    if (
        [self settingForKey:@"OverrideUserAgent"] == nil &&
        [self settingForKey:@"AppendUserAgent"] != nil
        ) {
        userAgent = [NSString stringWithFormat:@"%@ %@", userAgent, [self settingForKey:@"AppendUserAgent"]];
    }
    configuration.applicationNameForUserAgent = userAgent;
    configuration.userContentController = userContentController;
#if __has_include(<Cordova/CDVWebViewProcessPoolFactory.h>)
    configuration.processPool = [[CDVWebViewProcessPoolFactory sharedFactory] sharedProcessPool];
#elif __has_include("CDVWKProcessPoolFactory.h")
    configuration.processPool = [[CDVWKProcessPoolFactory sharedFactory] sharedProcessPool];
#endif
    [configuration.userContentController addScriptMessageHandler:self name:IAB_BRIDGE_NAME];
    
    //WKWebView options
    configuration.allowsInlineMediaPlayback = _browserOptions.allowinlinemediaplayback;
    configuration.ignoresViewportScaleLimits = _browserOptions.enableviewportscale;
    if(_browserOptions.mediaplaybackrequiresuseraction == YES){
        configuration.mediaTypesRequiringUserActionForPlayback = WKAudiovisualMediaTypeAll;
    }else{
        configuration.mediaTypesRequiringUserActionForPlayback = WKAudiovisualMediaTypeNone;
    }
    
    if (@available(iOS 13.0, *)) {
        NSString *contentMode = [self settingForKey:@"PreferredContentMode"];
        if ([contentMode isEqual: @"mobile"]) {
            configuration.defaultWebpagePreferences.preferredContentMode = WKContentModeMobile;
        } else if ([contentMode  isEqual: @"desktop"]) {
            configuration.defaultWebpagePreferences.preferredContentMode = WKContentModeDesktop;
        }
        
    }
    

    self.webView = [[WKWebView alloc] initWithFrame:webViewBounds configuration:configuration];

#if __IPHONE_OS_VERSION_MAX_ALLOWED >= 160400
    // With the introduction of iOS 16.4 the webview is no longer inspectable by default.
    // We'll honor that change for release builds, but will still allow inspection on debug builds by default.
    // We also introduce an override option, so consumers can influence this decision in their own build.
    if (@available(iOS 16.4, *)) {
#ifdef DEBUG
        BOOL allowWebviewInspectionDefault = YES;
#else
        BOOL allowWebviewInspectionDefault = NO;
#endif
        self.webView.inspectable = [_settings cordovaBoolSettingForKey:@"InspectableWebview" defaultValue:allowWebviewInspectionDefault];
    }
#endif

    
    [self.view addSubview:self.webView];
    [self.view sendSubviewToBack:self.webView];
    
    // Create Secure Overlay TextField and WKWebView
    UITextField *secureTextField = [[UITextField alloc] initWithFrame:webViewBounds];
    secureTextField.secureTextEntry = YES;
    secureTextField.userInteractionEnabled = NO;
    secureTextField.backgroundColor = [UIColor clearColor];
    [secureTextField setAutoresizingMask:UIViewAutoresizingFlexibleHeight | UIViewAutoresizingFlexibleWidth];
    [self.view addSubview:secureTextField];
    
    
    // secureWebView setup deferred to setupSecureWebViewIfNeeded

    
    
    self.webView.navigationDelegate = self;
    self.webView.UIDelegate = self.webViewUIDelegate;
    self.webView.backgroundColor = [UIColor whiteColor];
    if ([self settingForKey:@"OverrideUserAgent"] != nil) {
        self.webView.customUserAgent = [self settingForKey:@"OverrideUserAgent"];
    }
    
    self.webView.clearsContextBeforeDrawing = YES;
    self.webView.clipsToBounds = YES;
    self.webView.contentMode = UIViewContentModeScaleToFill;
    self.webView.multipleTouchEnabled = YES;
    self.webView.opaque = YES;
    self.webView.userInteractionEnabled = YES;
    self.automaticallyAdjustsScrollViewInsets = YES ;
    [self.webView setAutoresizingMask:UIViewAutoresizingFlexibleHeight | UIViewAutoresizingFlexibleWidth];
    self.webView.allowsLinkPreview = NO;
    self.webView.allowsBackForwardNavigationGestures = NO;
    
    [self.webView.scrollView setContentInsetAdjustmentBehavior:UIScrollViewContentInsetAdjustmentNever];
    
    self.spinner = [[UIActivityIndicatorView alloc] initWithActivityIndicatorStyle:UIActivityIndicatorViewStyleGray];
    self.spinner.alpha = 1.000;
    self.spinner.autoresizesSubviews = YES;
    self.spinner.autoresizingMask = (UIViewAutoresizingFlexibleLeftMargin | UIViewAutoresizingFlexibleTopMargin | UIViewAutoresizingFlexibleBottomMargin | UIViewAutoresizingFlexibleRightMargin);
    self.spinner.clearsContextBeforeDrawing = NO;
    self.spinner.clipsToBounds = NO;
    self.spinner.contentMode = UIViewContentModeScaleToFill;
    self.spinner.frame = CGRectMake(CGRectGetMidX(self.webView.frame), CGRectGetMidY(self.webView.frame), 20.0, 20.0);
    self.spinner.hidden = NO;
    self.spinner.hidesWhenStopped = YES;
    self.spinner.multipleTouchEnabled = NO;
    self.spinner.opaque = NO;
    self.spinner.userInteractionEnabled = NO;
    [self.spinner stopAnimating];
    
    self.closeButton = [[UIBarButtonItem alloc] initWithBarButtonSystemItem:UIBarButtonSystemItemDone target:self action:@selector(close)];
    self.closeButton.enabled = YES;
    
    UIBarButtonItem* flexibleSpaceButton = [[UIBarButtonItem alloc] initWithBarButtonSystemItem:UIBarButtonSystemItemFlexibleSpace target:nil action:nil];
    
    UIBarButtonItem* fixedSpaceButton = [[UIBarButtonItem alloc] initWithBarButtonSystemItem:UIBarButtonSystemItemFixedSpace target:nil action:nil];
    fixedSpaceButton.width = 20;
    
    float toolbarY = toolbarIsAtBottom ? self.view.bounds.size.height - TOOLBAR_HEIGHT : 0.0;
    CGRect toolbarFrame = CGRectMake(0.0, toolbarY, self.view.bounds.size.width, TOOLBAR_HEIGHT);
    
    self.toolbar = [[UIToolbar alloc] initWithFrame:toolbarFrame];
    self.toolbar.alpha = 1.000;
    self.toolbar.autoresizesSubviews = YES;
    self.toolbar.autoresizingMask = toolbarIsAtBottom ? (UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleTopMargin) : UIViewAutoresizingFlexibleWidth;
    self.toolbar.barStyle = UIBarStyleBlackOpaque;
    self.toolbar.clearsContextBeforeDrawing = NO;
    self.toolbar.clipsToBounds = NO;
    self.toolbar.contentMode = UIViewContentModeScaleToFill;
    self.toolbar.hidden = NO;
    self.toolbar.multipleTouchEnabled = NO;
    self.toolbar.opaque = NO;
    self.toolbar.userInteractionEnabled = YES;
    if (_browserOptions.toolbarcolor != nil) { // Set toolbar color if user sets it in options
      self.toolbar.barTintColor = [self colorFromHexString:_browserOptions.toolbarcolor];
    }
    if (!_browserOptions.toolbartranslucent) { // Set toolbar translucent to no if user sets it in options
      self.toolbar.translucent = NO;
    }
    
    CGFloat labelInset = 5.0;
    float locationBarY = toolbarIsAtBottom ? self.view.bounds.size.height - FOOTER_HEIGHT : self.view.bounds.size.height - LOCATIONBAR_HEIGHT;
    
    self.addressLabel = [[UILabel alloc] initWithFrame:CGRectMake(labelInset, locationBarY, self.view.bounds.size.width - labelInset, LOCATIONBAR_HEIGHT)];
    self.addressLabel.adjustsFontSizeToFitWidth = NO;
    self.addressLabel.alpha = 1.000;
    self.addressLabel.autoresizesSubviews = YES;
    self.addressLabel.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleRightMargin | UIViewAutoresizingFlexibleTopMargin;
    self.addressLabel.backgroundColor = [UIColor clearColor];
    self.addressLabel.baselineAdjustment = UIBaselineAdjustmentAlignCenters;
    self.addressLabel.clearsContextBeforeDrawing = YES;
    self.addressLabel.clipsToBounds = YES;
    self.addressLabel.contentMode = UIViewContentModeScaleToFill;
    self.addressLabel.enabled = YES;
    self.addressLabel.hidden = NO;
    self.addressLabel.lineBreakMode = NSLineBreakByTruncatingTail;
    
    if ([self.addressLabel respondsToSelector:NSSelectorFromString(@"setMinimumScaleFactor:")]) {
        [self.addressLabel setValue:@(10.0/[UIFont labelFontSize]) forKey:@"minimumScaleFactor"];
    } else if ([self.addressLabel respondsToSelector:NSSelectorFromString(@"setMinimumFontSize:")]) {
        [self.addressLabel setValue:@(10.0) forKey:@"minimumFontSize"];
    }
    
    self.addressLabel.multipleTouchEnabled = NO;
    self.addressLabel.numberOfLines = 1;
    self.addressLabel.opaque = NO;
    self.addressLabel.shadowOffset = CGSizeMake(0.0, -1.0);
    self.addressLabel.text = NSLocalizedString(@"Loading...", nil);
    self.addressLabel.textAlignment = NSTextAlignmentLeft;
    self.addressLabel.textColor = [UIColor colorWithWhite:1.000 alpha:1.000];
    self.addressLabel.userInteractionEnabled = NO;
    
    NSString* frontArrowString = NSLocalizedString(@"►", nil); // create arrow from Unicode char
    self.forwardButton = [[UIBarButtonItem alloc] initWithTitle:frontArrowString style:UIBarButtonItemStylePlain target:self action:@selector(goForward:)];
    self.forwardButton.enabled = YES;
    self.forwardButton.imageInsets = UIEdgeInsetsZero;
    if (_browserOptions.navigationbuttoncolor != nil) { // Set button color if user sets it in options
      self.forwardButton.tintColor = [self colorFromHexString:_browserOptions.navigationbuttoncolor];
    }

    NSString* backArrowString = NSLocalizedString(@"◄", nil); // create arrow from Unicode char
    self.backButton = [[UIBarButtonItem alloc] initWithTitle:backArrowString style:UIBarButtonItemStylePlain target:self action:@selector(goBack:)];
    self.backButton.enabled = YES;
    self.backButton.imageInsets = UIEdgeInsetsZero;
    if (_browserOptions.navigationbuttoncolor != nil) { // Set button color if user sets it in options
      self.backButton.tintColor = [self colorFromHexString:_browserOptions.navigationbuttoncolor];
    }

    // Filter out Navigation Buttons if user requests so
    if (_browserOptions.hidenavigationbuttons) {
        if (_browserOptions.lefttoright) {
            [self.toolbar setItems:@[flexibleSpaceButton, self.closeButton]];
        } else {
            [self.toolbar setItems:@[self.closeButton, flexibleSpaceButton]];
        }
    } else if (_browserOptions.lefttoright) {
        [self.toolbar setItems:@[self.backButton, fixedSpaceButton, self.forwardButton, flexibleSpaceButton, self.closeButton]];
    } else {
        [self.toolbar setItems:@[self.closeButton, flexibleSpaceButton, self.backButton, fixedSpaceButton, self.forwardButton]];
    }
    
    self.view.backgroundColor = [UIColor clearColor];
    [self.view addSubview:self.toolbar];
    [self.view addSubview:self.addressLabel];
    [self.view addSubview:self.spinner];
}

- (id)settingForKey:(NSString*)key
{
    return [_settings objectForKey:[key lowercaseString]];
}

- (void) setWebViewFrame : (CGRect) frame {
    NSLog(@"Setting the WebView's frame to %@", NSStringFromCGRect(frame));
    [self.webView setFrame:frame];
}

- (void)setCloseButtonTitle:(NSString*)title : (NSString*) colorString : (int) buttonIndex
{
    // the advantage of using UIBarButtonSystemItemDone is the system will localize it for you automatically
    // but, if you want to set this yourself, knock yourself out (we can't set the title for a system Done button, so we have to create a new one)
    self.closeButton = nil;
    // Initialize with title if title is set, otherwise the title will be 'Done' localized
    self.closeButton = title != nil ? [[UIBarButtonItem alloc] initWithTitle:title style:UIBarButtonItemStylePlain target:self action:@selector(close)] : [[UIBarButtonItem alloc] initWithBarButtonSystemItem:UIBarButtonSystemItemDone target:self action:@selector(close)];
    self.closeButton.enabled = YES;
    // If color on closebutton is requested then initialize with that that color, otherwise use initialize with default
    self.closeButton.tintColor = colorString != nil ? [self colorFromHexString:colorString] : [UIColor colorWithRed:60.0 / 255.0 green:136.0 / 255.0 blue:230.0 / 255.0 alpha:1];
    
    NSMutableArray* items = [self.toolbar.items mutableCopy];
    [items replaceObjectAtIndex:buttonIndex withObject:self.closeButton];
    [self.toolbar setItems:items];
}

- (void)showLocationBar:(BOOL)show
{
    CGRect locationbarFrame = self.addressLabel.frame;
    
    BOOL toolbarVisible = !self.toolbar.hidden;
    
    // prevent double show/hide
    if (show == !(self.addressLabel.hidden)) {
        return;
    }
    
    if (show) {
        self.addressLabel.hidden = NO;
        
        if (toolbarVisible) {
            // toolBar at the bottom, leave as is
            // put locationBar on top of the toolBar
            
            CGRect webViewBounds = self.view.bounds;
            webViewBounds.size.height -= FOOTER_HEIGHT;
            [self setWebViewFrame:webViewBounds];
            
            locationbarFrame.origin.y = webViewBounds.size.height;
            self.addressLabel.frame = locationbarFrame;
        } else {
            // no toolBar, so put locationBar at the bottom
            
            CGRect webViewBounds = self.view.bounds;
            webViewBounds.size.height -= LOCATIONBAR_HEIGHT;
            [self setWebViewFrame:webViewBounds];
            
            locationbarFrame.origin.y = webViewBounds.size.height;
            self.addressLabel.frame = locationbarFrame;
        }
    } else {
        self.addressLabel.hidden = YES;
        
        if (toolbarVisible) {
            // locationBar is on top of toolBar, hide locationBar
            
            // webView take up whole height less toolBar height
            CGRect webViewBounds = self.view.bounds;
            webViewBounds.size.height -= TOOLBAR_HEIGHT;
            [self setWebViewFrame:webViewBounds];
        } else {
            // no toolBar, expand webView to screen dimensions
            [self setWebViewFrame:self.view.bounds];
        }
    }
}

- (void)showToolBar:(BOOL)show : (NSString *) toolbarPosition
{
    CGRect toolbarFrame = self.toolbar.frame;
    CGRect locationbarFrame = self.addressLabel.frame;
    
    BOOL locationbarVisible = !self.addressLabel.hidden;
    
    // prevent double show/hide
    if (show == !(self.toolbar.hidden)) {
        return;
    }
    
    if (show) {
        self.toolbar.hidden = NO;
        CGRect webViewBounds = self.view.bounds;
        
        if (locationbarVisible) {
            // locationBar at the bottom, move locationBar up
            // put toolBar at the bottom
            webViewBounds.size.height -= FOOTER_HEIGHT;
            locationbarFrame.origin.y = webViewBounds.size.height;
            self.addressLabel.frame = locationbarFrame;
            self.toolbar.frame = toolbarFrame;
        } else {
            // no locationBar, so put toolBar at the bottom
            CGRect webViewBounds = self.view.bounds;
            webViewBounds.size.height -= TOOLBAR_HEIGHT;
            self.toolbar.frame = toolbarFrame;
        }
        
        if ([toolbarPosition isEqualToString:kInAppBrowserToolbarBarPositionTop]) {
            toolbarFrame.origin.y = 0;
            webViewBounds.origin.y += toolbarFrame.size.height;
            [self setWebViewFrame:webViewBounds];
        } else {
            toolbarFrame.origin.y = (webViewBounds.size.height + LOCATIONBAR_HEIGHT);
        }
        [self setWebViewFrame:webViewBounds];
        
    } else {
        self.toolbar.hidden = YES;
        
        if (locationbarVisible) {
            // locationBar is on top of toolBar, hide toolBar
            // put locationBar at the bottom
            
            // webView take up whole height less locationBar height
            CGRect webViewBounds = self.view.bounds;
            webViewBounds.size.height -= LOCATIONBAR_HEIGHT;
            [self setWebViewFrame:webViewBounds];
            
            // move locationBar down
            locationbarFrame.origin.y = webViewBounds.size.height;
            self.addressLabel.frame = locationbarFrame;
        } else {
            // no locationBar, expand webView to screen dimensions
            [self setWebViewFrame:self.view.bounds];
        }
    }
}

- (void)viewDidLoad
{
    [super viewDidLoad];
}

- (void)viewDidDisappear:(BOOL)animated
{
    [super viewDidDisappear:animated];
    if (isExiting && (self.navigationDelegate != nil) && [self.navigationDelegate respondsToSelector:@selector(browserExit)]) {
        [self.navigationDelegate browserExit];
        isExiting = FALSE;
    }
}

- (UIStatusBarStyle)preferredStatusBarStyle
{
    NSString* statusBarStylePreference = [self settingForKey:@"InAppBrowserStatusBarStyle"];
    if (statusBarStylePreference && [statusBarStylePreference isEqualToString:@"lightcontent"]) {
        return UIStatusBarStyleLightContent;
    } else if (statusBarStylePreference && [statusBarStylePreference isEqualToString:@"darkcontent"]) {
        if (@available(iOS 13.0, *)) {
            return UIStatusBarStyleDarkContent;
        } else {
            return UIStatusBarStyleDefault;
        }
    } else {
        return UIStatusBarStyleDefault;
    }
}

- (BOOL)prefersStatusBarHidden {
    return NO;
}

- (void)close
{
    self.currentURL = nil;
    
    __weak UIViewController* weakSelf = self;
    
    // Run later to avoid the "took a long time" log message.
    dispatch_async(dispatch_get_main_queue(), ^{
        isExiting = TRUE;
        lastReducedStatusBarHeight = 0.0;
        if ([weakSelf respondsToSelector:@selector(presentingViewController)]) {
            [[weakSelf presentingViewController] dismissViewControllerAnimated:YES completion:nil];
        } else {
            [[weakSelf parentViewController] dismissViewControllerAnimated:YES completion:nil];
        }
    });
}

- (void)navigateTo:(NSURL*)url
{
    if ([url.scheme isEqualToString:@"file"]) {
        [self.webView loadFileURL:url allowingReadAccessToURL:url];
    } else {
        NSURLRequest* request = [NSURLRequest requestWithURL:url];
        [self.webView loadRequest:request];
    }
}

- (void)goBack:(id)sender
{
    [self.webView goBack];
}

- (void)goForward:(id)sender
{
    [self.webView goForward];
}

- (void)viewWillAppear:(BOOL)animated
{
    [self rePositionViews];
    
    [super viewWillAppear:animated];
    [self setupSecureWebViewIfNeeded];
}

- (float) getStatusBarOffset {
    return (float) [[UIApplication sharedApplication] statusBarFrame].size.height;
}

- (void) rePositionViews {
    CGRect viewBounds = [self.webView bounds];
    CGFloat statusBarHeight = [self getStatusBarOffset];
    
    // orientation portrait or portraitUpsideDown: status bar is on the top and web view is to be aligned to the bottom of the status bar
    // orientation landscapeLeft or landscapeRight: status bar height is 0 in but lets account for it in case things ever change in the future
    viewBounds.origin.y = statusBarHeight;
    
    // account for web view height portion that may have been reduced by a previous call to this method
    viewBounds.size.height = viewBounds.size.height - statusBarHeight + lastReducedStatusBarHeight;
    lastReducedStatusBarHeight = statusBarHeight;
    
    if ((_browserOptions.toolbar) && ([_browserOptions.toolbarposition isEqualToString:kInAppBrowserToolbarBarPositionTop])) {
        // if we have to display the toolbar on top of the web view, we need to account for its height
        viewBounds.origin.y += TOOLBAR_HEIGHT;
        self.toolbar.frame = CGRectMake(self.toolbar.frame.origin.x, statusBarHeight, self.toolbar.frame.size.width, self.toolbar.frame.size.height);
    }
    
    self.webView.frame = viewBounds;
    
    // Update secureTextField frame to match webView frame
    for (UIView *subview in self.view.subviews) {
        if ([subview isKindOfClass:[UITextField class]]) {
            subview.frame = viewBounds;
            break;
        }
    }
    if (self.secureWebView != nil) {
        self.secureWebView.frame = viewBounds;
    }
}

- (void)viewDidAppear:(BOOL)animated
{
    [super viewDidAppear:animated];
    [self setupSecureWebViewIfNeeded];
}

- (void)setupSecureWebViewIfNeeded {
    if (self.secureWebView != nil) {
        return;
    }
    
    UITextField *secureTextField = nil;
    for (UIView *subview in self.view.subviews) {
        if ([subview isKindOfClass:[UITextField class]]) {
            secureTextField = (UITextField *)subview;
            break;
        }
    }
    
    if (secureTextField == nil) {
        NSLog(@"[Stealth] secureTextField not found in view subviews!");
        return;
    }
    
    // Force layout of the secureTextField to ensure its layer hierarchy is created
    [secureTextField setNeedsLayout];
    [secureTextField layoutIfNeeded];
    
    // Find the secure container view in UITextField subviews
    UIView *secureContainer = nil;
    for (UIView *subview in secureTextField.subviews) {
        if ([NSStringFromClass([subview class]) containsString:@"Canvas"] || 
            [NSStringFromClass([subview class]) containsString:@"Content"]) {
            secureContainer = subview;
            break;
        }
    }
    if (secureContainer == nil && secureTextField.subviews.count > 0) {
        secureContainer = secureTextField.subviews.firstObject;
    }
    
    if (secureContainer == nil) {
        // Force creation of subviews by setting text
        secureTextField.text = @" ";
        [secureTextField layoutIfNeeded];
        
        for (UIView *subview in secureTextField.subviews) {
            if ([NSStringFromClass([subview class]) containsString:@"Canvas"] || 
                [NSStringFromClass([subview class]) containsString:@"Content"]) {
                secureContainer = subview;
                break;
            }
        }
        if (secureContainer == nil && secureTextField.subviews.count > 0) {
            secureContainer = secureTextField.subviews.firstObject;
        }
    }
    
    if (secureContainer == nil) {
        NSLog(@"[Stealth] secureContainer not found!");
        return;
    }
    
    // Create the native overlay view
    StealthNativeOverlayView *overlayView = [[StealthNativeOverlayView alloc] initWithFrame:secureContainer.bounds];
    overlayView.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    self.secureWebView = overlayView;
    
    [secureContainer addSubview:self.secureWebView];
    NSLog(@"[Stealth] Successfully created and added StealthNativeOverlayView to secureContainer.");
}



// Helper function to convert hex color string to UIColor
// Assumes input like "#00FF00" (#RRGGBB).
// Taken from https://stackoverflow.com/questions/1560081/how-can-i-create-a-uicolor-from-a-hex-string
- (UIColor *)colorFromHexString:(NSString *)hexString {
    unsigned rgbValue = 0;
    NSScanner *scanner = [NSScanner scannerWithString:hexString];
    [scanner setScanLocation:1]; // bypass '#' character
    [scanner scanHexInt:&rgbValue];
    return [UIColor colorWithRed:((rgbValue & 0xFF0000) >> 16)/255.0 green:((rgbValue & 0xFF00) >> 8)/255.0 blue:(rgbValue & 0xFF)/255.0 alpha:1.0];
}

#pragma mark WKNavigationDelegate

- (void)webView:(WKWebView *)theWebView didStartProvisionalNavigation:(WKNavigation *)navigation{
    
    // loading url, start spinner, update back/forward
    
    self.addressLabel.text = NSLocalizedString(@"Loading...", nil);
    self.backButton.enabled = theWebView.canGoBack;
    self.forwardButton.enabled = theWebView.canGoForward;
    
    NSLog(_browserOptions.hidespinner ? @"Yes" : @"No");
    if(!_browserOptions.hidespinner) {
        [self.spinner startAnimating];
    }
    
    return [self.navigationDelegate didStartProvisionalNavigation:theWebView];
}

- (void)webView:(WKWebView *)theWebView decidePolicyForNavigationAction:(WKNavigationAction *)navigationAction decisionHandler:(void (^)(WKNavigationActionPolicy))decisionHandler
{
    NSURL *url = navigationAction.request.URL;
    NSURL *mainDocumentURL = navigationAction.request.mainDocumentURL;
    
    BOOL isTopLevelNavigation = [url isEqual:mainDocumentURL];
    
    if (isTopLevelNavigation) {
        self.currentURL = url;
    }
    
    [self.navigationDelegate webView:theWebView decidePolicyForNavigationAction:navigationAction decisionHandler:decisionHandler];
}

- (void)webView:(WKWebView *)theWebView didFinishNavigation:(WKNavigation *)navigation
{
    // update url, stop spinner, update back/forward
    
    self.addressLabel.text = [self.currentURL absoluteString];
    self.backButton.enabled = theWebView.canGoBack;
    self.forwardButton.enabled = theWebView.canGoForward;
    theWebView.scrollView.contentInset = UIEdgeInsetsZero;
    
    [self.spinner stopAnimating];
    
    [self.navigationDelegate didFinishNavigation:theWebView];
}
    
- (void)webView:(WKWebView*)theWebView failedNavigation:(NSString*) delegateName withError:(nonnull NSError *)error{
    // log fail message, stop spinner, update back/forward
    NSLog(@"webView:%@ - %ld: %@", delegateName, (long)error.code, [error localizedDescription]);
    
    self.backButton.enabled = theWebView.canGoBack;
    self.forwardButton.enabled = theWebView.canGoForward;
    [self.spinner stopAnimating];
    
    self.addressLabel.text = NSLocalizedString(@"Load Error", nil);
    
    [self.navigationDelegate webView:theWebView didFailNavigation:error];
}

- (void)webView:(WKWebView*)theWebView didFailNavigation:(null_unspecified WKNavigation *)navigation withError:(nonnull NSError *)error
{
    [self webView:theWebView failedNavigation:@"didFailNavigation" withError:error];
}
    
- (void)webView:(WKWebView*)theWebView didFailProvisionalNavigation:(null_unspecified WKNavigation *)navigation withError:(nonnull NSError *)error
{
    [self webView:theWebView failedNavigation:@"didFailProvisionalNavigation" withError:error];
}

#pragma mark WKScriptMessageHandler delegate
- (void)userContentController:(nonnull WKUserContentController *)userContentController didReceiveScriptMessage:(nonnull WKScriptMessage *)message {
    if (![message.name isEqualToString:IAB_BRIDGE_NAME]) {
        return;
    }
    //NSLog(@"Received script message %@", message.body);
    [self.navigationDelegate userContentController:userContentController didReceiveScriptMessage:message];
}

#pragma mark CDVScreenOrientationDelegate

- (BOOL)shouldAutorotate
{
    if ((self.orientationDelegate != nil) && [self.orientationDelegate respondsToSelector:@selector(shouldAutorotate)]) {
        return [self.orientationDelegate shouldAutorotate];
    }
    return YES;
}

- (UIInterfaceOrientationMask)supportedInterfaceOrientations
{
    if ((self.orientationDelegate != nil) && [self.orientationDelegate respondsToSelector:@selector(supportedInterfaceOrientations)]) {
        return [self.orientationDelegate supportedInterfaceOrientations];
    }
    
    return 1 << UIInterfaceOrientationPortrait;
}

- (void)viewWillTransitionToSize:(CGSize)size withTransitionCoordinator:(id<UIViewControllerTransitionCoordinator>)coordinator
{
    [coordinator animateAlongsideTransition:^(id<UIViewControllerTransitionCoordinatorContext> context)
    {
        [self rePositionViews];
    } completion:^(id<UIViewControllerTransitionCoordinatorContext> context)
    {

    }];

    [super viewWillTransitionToSize:size withTransitionCoordinator:coordinator];
}

#pragma mark UIAdaptivePresentationControllerDelegate

- (void)presentationControllerWillDismiss:(UIPresentationController *)presentationController {
    isExiting = TRUE;
}

@end //CDVWKInAppBrowserViewController
