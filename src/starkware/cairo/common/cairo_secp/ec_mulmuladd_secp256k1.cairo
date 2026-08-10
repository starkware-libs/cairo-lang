//*************************************************************************************/
///* Copyright (C) 2022 - Renaud Dubois - This file is part of Cairo_musig2 project	 */
///* License: This software is licensed under a dual BSD and GPL v2 license. 	 */
///* See LICENSE file at the root folder of the project.				 */
///* FILE: multipoint.cairo							         */
///* 											 */
///* 											 */
///* DESCRIPTION: optimization of dual base multiplication*/
///* the algorithm combines the so called Shamir's trick with Windowing method	  */
//**************************************************************************************/

//Shamir's trick:https://crypto.stackexchange.com/questions/99975/strauss-shamir-trick-on-ec-multiplication-by-scalar,
//Windowing method : https://en.wikipedia.org/wiki/Exponentiation_by_squaring, section 'sliding window'
//The implementation use a 2 bits window with trick, leading to a 16 points elliptic point precomputation


from starkware.cairo.common.cairo_builtins import EcOpBuiltin 
from starkware.cairo.common.registers import get_ap
from starkware.cairo.common.registers import get_fp_and_pc

from starkware.cairo.common.uint256 import Uint256

from starkware.cairo.common.math_cmp import is_nn_le

from starkware.cairo.common.cairo_secp.bigint import BigInt3, UnreducedBigInt3, nondet_bigint3
from starkware.cairo.common.cairo_secp.field import (
    is_zero,
    unreduced_mul,
    unreduced_sqr,
    verify_zero,
)
from starkware.cairo.common.cairo_secp.constants import BETA, N0, N1, N2
from starkware.cairo.common.cairo_secp.ec import EcPoint, ec_add, ec_mul, ec_negate, ec_double
from cairo_secp.ec_mulmuladd import ec_mulmuladd_inner, ec_mulmuladd_W_inner, Window





func ec_mulmuladd_bg3{range_check_ptr}(G: EcPoint, Q: EcPoint, scalar_u: BigInt3, scalar_v: BigInt3) -> (res: EcPoint){

    alloc_locals;
    local len_hi; 
    local len_med; 
    local len_low;
    
    //Precompute H=P+Q
    let H:EcPoint=ec_add{range_check_ptr=range_check_ptr}(G,Q);
   
    //initialize R with infinity point
    let R = EcPoint(BigInt3(0, 0, 0), BigInt3(0, 0, 0));
    
     //recover MSB bit index of high part
    %{ ids.len_hi=max(ids.scalar_u.d2.bit_length(), ids.scalar_v.d2.bit_length())-1 %}    
    //%{ print("\n length=", ids.len_hi) %}
    let (hiR:EcPoint)=ec_mulmuladd_inner(R,G,Q,H, scalar_u.d2, scalar_v.d2, len_hi);

    //recover MSB bit index of med part
    %{ ids.len_med=max(ids.scalar_u.d1.bit_length(), ids.scalar_v.d1.bit_length())-1 %}    
    //%{ print("\n length=", ids.len_med) %}
    let (medR:EcPoint)=ec_mulmuladd_inner(hiR,G,Q,H, scalar_u.d1, scalar_v.d1, len_med);
 
    //recover MSB bit index of low part
    %{ ids.len_low=max(ids.scalar_u.d0.bit_length(), ids.scalar_v.d0.bit_length())-1 %}    
    //%{ print("\n length=", ids.len_low) %}

    let (lowR:EcPoint)=ec_mulmuladd_inner(medR,G,Q,H, scalar_u.d0, scalar_v.d0, len_low);

    return (res=lowR);
}


func ec_mulmuladdW_bg3{range_check_ptr}(G: EcPoint, Q: EcPoint, scalar_u: BigInt3, scalar_v: BigInt3) -> (res: EcPoint){
    alloc_locals;
    local len_hi; //hi 84 bits part of scalar
    local len_med; //med 86 bits part
    local len_low;//low bits part
    
    //Precompute a 4-bit window , W0=infty, W1=P, W2=Q, the window is indexed by (8*v1 4*u1+ 2*v0 + u0), where (u1,u0) represents two bit of scalar u, (resp for v)
    
    let W3:EcPoint=ec_add{range_check_ptr=range_check_ptr}(G,Q); //3:G+Q
    let W4:EcPoint=ec_double{range_check_ptr=range_check_ptr}(G); //4:2G
    let W5:EcPoint=ec_add{range_check_ptr=range_check_ptr}(G,W4); //5:3G
    let W6:EcPoint=ec_add{range_check_ptr=range_check_ptr}(W4,Q); //6:2G+Q
    let W7:EcPoint=ec_add{range_check_ptr=range_check_ptr}(W5,Q); //7:3G+Q
    let W8:EcPoint=ec_double{range_check_ptr=range_check_ptr}(Q); //8:2Q
    
    let W9:EcPoint=ec_add{range_check_ptr=range_check_ptr}(W8,G); //9:2Q+G
    let W10:EcPoint=ec_add{range_check_ptr=range_check_ptr}(W8,Q); //10:3Q
    let W11:EcPoint=ec_add{range_check_ptr=range_check_ptr}(W10,G); //11:3Q+G
    let W12:EcPoint=ec_add{range_check_ptr=range_check_ptr}(W8,W4); //12:2Q+2G
    let W13:EcPoint=ec_add{range_check_ptr=range_check_ptr}(W8,W5); //13:2Q+3G
    let W14:EcPoint=ec_add{range_check_ptr=range_check_ptr}(W10,W4); //14:3Q+2G
    let W15:EcPoint=ec_add{range_check_ptr=range_check_ptr}(W10,W5); //15:3Q+3G
   
    let PrecPoint:Window=Window( G,Q,W3, W4, W5, W6, W7, W8, W9, W10, W11, W12, W13, W14, W15);
   
  
    //initialize R with infinity point
    let R = EcPoint(BigInt3(0, 0, 0), BigInt3(0, 0, 0));
    
    %{ ids.len_hi=max(ids.scalar_u.d2.bit_length(), ids.scalar_v.d2.bit_length())-1 %}    
    //%{ print("\n length=", ids.len_hi) %}
   
    let (hiR:EcPoint)=ec_mulmuladd_W_inner(R, PrecPoint, scalar_u.d2, scalar_v.d2, len_hi);
    
    let (medR:EcPoint)=ec_mulmuladd_W_inner(hiR, PrecPoint, scalar_u.d1, scalar_v.d1, 85);
    
    let (lowR:EcPoint)=ec_mulmuladd_W_inner(medR, PrecPoint, scalar_u.d0, scalar_v.d0, 85);
   
   
    return (res=lowR);	
    

}







