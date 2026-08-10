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

//Structure storing all aP+b.Q for (a,b) in [0..3]x[0..3]
struct Window {
    G: EcPoint,
    Q: EcPoint,
    W3: EcPoint,
    W4: EcPoint,
    W5: EcPoint,
    W6: EcPoint,
    W7: EcPoint,
    W8: EcPoint,
    W9: EcPoint,
    W10: EcPoint,
    W11: EcPoint,
    W12: EcPoint,
    W13: EcPoint,
    W14: EcPoint,
    W15: EcPoint,
}



//https://crypto.stackexchange.com/questions/99975/strauss-shamir-trick-on-ec-multiplication-by-scalar,
//* Internal call for recursion of point multiplication via Shamir's trick */
func ec_mulmuladd_inner{range_check_ptr}(R: EcPoint, G: EcPoint, Q: EcPoint, H: EcPoint,scalar_u: felt, scalar_v: felt, m: felt) -> (res: EcPoint){
   

    alloc_locals;
      //this means if m=-1, beware if felt definition changes
    if(m == 3618502788666131213697322783095070105623107215331596699973092056135872020480){
    //%{ print("\n end of recursion" ) %}
     return(res=R);
    }
    
    let (double_point: EcPoint) = ec_double(R);
    //   %{ print("\n double" ) %}
 
    let mm1:felt=m-1;
    local dibit;
    
    //extract MSB values of both exponents
     %{ ids.dibit = ((ids.scalar_u >>ids.m)&1) +2*((ids.scalar_v >>ids.m)&1) %}
     //%{ print("\n ui=",ids.scalar_u >>ids.m, "\n vi=", ids.scalar_v >>ids.m) %}
    	
    //set R:=R+R
    if(dibit==0){
    	let (res:EcPoint)= ec_mulmuladd_inner(double_point,G,Q,H,scalar_u,scalar_v,mm1 );
    	return(res=res);
    }
    //if ui=1 and vi=0, set R:=R+G
    if(dibit==1){
    	let (res10:EcPoint)=ec_add(double_point,G);
    	let (res:EcPoint)= ec_mulmuladd_inner(res10,G,Q,H,scalar_u,scalar_v,mm1 );
    	return(res=res);
    }
    //(else) if ui=0 and vi=1, set R:=R+Q
    if(dibit==2){
    	let (res01:EcPoint)=ec_add(double_point,Q);
    	let (res:EcPoint)= ec_mulmuladd_inner(res01,G,Q,H,scalar_u,scalar_v,mm1 );
    	return(res=res);
        }
    //(else) if ui=1 and vi=1, set R:=R+Q
    if(dibit==3){
   	let (res11:EcPoint)=ec_add(double_point,H);
    	let (res:EcPoint)= ec_mulmuladd_inner(res11,G,Q,H,scalar_u,scalar_v,mm1 );
    	
    	return(res=res);
    }
    
     //you shall never end up here
     return(res=R);
}



//https://crypto.stackexchange.com/questions/99975/strauss-shamir-trick-on-ec-multiplication-by-scalar,
//* Internal call for recursion of point multiplication via Shamir's trick+Windowed method */
func ec_mulmuladd_W_inner{range_check_ptr}(R: EcPoint, Prec:Window, scalar_u: felt, scalar_v: felt, m: felt) -> (res: EcPoint){
    alloc_locals;
    let mm1:felt=m-2;
    local quad_bit;//(8*v1 4*u1+ 2*v0 + u0), where (u1,u0) represents two bit at index m of scalar u, (resp for v)
    
    if(m == -1){
    //%{ print("\n end of recursion, no add" ) %}
     return(res=R);
    }
   
    let (double_point: EcPoint) = ec_double(R);
     //  %{ print("\n double" ) %}
 
     //still have to make the last addition over 1 bit (initial length was odd)
    if(m == 0){
     %{ print("\n end of recursion, one bit" ) %}
     let (res:EcPoint)=ec_mulmuladd_inner(R, Prec.G, Prec.Q, Prec.W3, scalar_u, scalar_v, m);
     
     return(res=res);
    }
   
    let (quadruple_point: EcPoint) = ec_double(double_point);
    //%{ print("\n double" ) %}
 	
 
    //compute quadruple (8*v1 4*u1+ 2*v0 + u0)
     %{ ids.quad_bit = 8*((ids.scalar_v >>ids.m)&1) +4*((ids.scalar_u >>ids.m)&1) +2*((ids.scalar_v >>(ids.m-1))&1)+((ids.scalar_u >>(ids.m-1))&1)    %}
    // %{ print("\n index=",ids.m , "quad_bit=", ids.quad_bit) %}
  
     if(quad_bit==0){
   	     let (res:EcPoint)=ec_mulmuladd_W_inner(quadruple_point, Prec, scalar_u, scalar_v, m-2);
    	     return(res=res);
     }
     if(quad_bit==1){
	     let (ecTemp:EcPoint)=ec_add(quadruple_point,Prec.G);
	     let (res:EcPoint)=ec_mulmuladd_W_inner(ecTemp, Prec, scalar_u, scalar_v, m-2);
    
    	     return(res=res);
     }
     if(quad_bit==2){
	     let (ecTemp:EcPoint)=ec_add(quadruple_point,Prec.Q);
	     let (res:EcPoint)=ec_mulmuladd_W_inner(ecTemp, Prec, scalar_u, scalar_v, m-2);
    	     return(res=res);
     }
     
     if(quad_bit==3){
	     let (ecTemp:EcPoint)=ec_add(quadruple_point,Prec.W3);
	     let (res:EcPoint)=ec_mulmuladd_W_inner(ecTemp, Prec, scalar_u, scalar_v, m-2);  
    	     return(res=res);
     }
     if(quad_bit==4){
	     let (ecTemp:EcPoint)=ec_add(quadruple_point,Prec.W4);
      	     let (res:EcPoint)=ec_mulmuladd_W_inner(ecTemp, Prec, scalar_u, scalar_v, m-2);
      	     return(res=res);
     }
     if(quad_bit==5){
     let (ecTemp:EcPoint)=ec_add(quadruple_point,Prec.W5);
     let (res:EcPoint)=ec_mulmuladd_W_inner(ecTemp, Prec, scalar_u, scalar_v, m-2);
      	     return(res=res);
     }
     if(quad_bit==6){
     let (ecTemp:EcPoint)=ec_add(quadruple_point,Prec.W6);
     let (res:EcPoint)=ec_mulmuladd_W_inner(ecTemp, Prec, scalar_u, scalar_v, m-2);
      	     return(res=res);
     }
     if(quad_bit==7){
     let (ecTemp:EcPoint)=ec_add(quadruple_point,Prec.W7);
     let (res:EcPoint)=ec_mulmuladd_W_inner(ecTemp, Prec, scalar_u, scalar_v, m-2);
      	     return(res=res);
     }
     if(quad_bit==8){
     let (ecTemp:EcPoint)=ec_add(quadruple_point,Prec.W8);
     let (res:EcPoint)=ec_mulmuladd_W_inner(ecTemp, Prec, scalar_u, scalar_v, m-2);
      	     return(res=res);
     }
     if(quad_bit==9){
     let (ecTemp:EcPoint)=ec_add(quadruple_point,Prec.W9);
     let (res:EcPoint)=ec_mulmuladd_W_inner(ecTemp, Prec, scalar_u, scalar_v, m-2);
      	     return(res=res);
     }
     if(quad_bit==10){
     let (ecTemp:EcPoint)=ec_add(quadruple_point,Prec.W10);
     let (res:EcPoint)=ec_mulmuladd_W_inner(ecTemp, Prec, scalar_u, scalar_v, m-2);
      	     return(res=res);
     }
     if(quad_bit==11){
     let (ecTemp:EcPoint)=ec_add(quadruple_point,Prec.W11);
     let (res:EcPoint)=ec_mulmuladd_W_inner(ecTemp, Prec, scalar_u, scalar_v, m-2);
      	     return(res=res);
     }
     if(quad_bit==12){
     let (ecTemp:EcPoint)=ec_add(quadruple_point,Prec.W12);
     let (res:EcPoint)=ec_mulmuladd_W_inner(ecTemp, Prec, scalar_u, scalar_v, m-2);
      	     return(res=res);
     }
     if(quad_bit==13){
     let (ecTemp:EcPoint)=ec_add(quadruple_point,Prec.W13);
     let (res:EcPoint)=ec_mulmuladd_W_inner(ecTemp, Prec, scalar_u, scalar_v, m-2);
      	     return(res=res);
     }
     if(quad_bit==14){
     let (ecTemp:EcPoint)=ec_add(quadruple_point,Prec.W14);
     let (res:EcPoint)=ec_mulmuladd_W_inner(ecTemp, Prec, scalar_u, scalar_v, m-2);
      	     return(res=res);
     }
     if(quad_bit==15){
     let (ecTemp:EcPoint)=ec_add(quadruple_point,Prec.W15);
     let (res:EcPoint)=ec_mulmuladd_W_inner(ecTemp, Prec, scalar_u, scalar_v, m-2);
      	     return(res=res);
     }
  
    //shall not be reach
    return(res=R);
}

//https://crypto.stackexchange.com/questions/99975/strauss-shamir-trick-on-ec-multiplication-by-scalar,
//further optimized with 'windowing method'
func ec_mulmuladd_W{range_check_ptr}(G: EcPoint, Q: EcPoint, scalar_u: felt, scalar_v: felt) -> (res: EcPoint){

    alloc_locals;
    local m;
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
   
     //[ap]=0, ap++;
     
     //let test:EcPoint=ec_add{range_check_ptr=range_check_ptr}(Window_Points[0],Window_Points[1]); //15:3Q+3G
  
    //recover MSB bit index
    %{ ids.m=max(ids.scalar_u.bit_length(), ids.scalar_v.bit_length())-1 %}    
    %{ print("\n window scalar length=", ids.m) %}
    //initialize R with infinity point
    let R = EcPoint(BigInt3(0, 0, 0), BigInt3(0, 0, 0));
   
    let (resu:EcPoint)=ec_mulmuladd_W_inner(R, PrecPoint, scalar_u, scalar_v, m);
   
   
    return (res=resu);	
}


//https://crypto.stackexchange.com/questions/99975/strauss-shamir-trick-on-ec-multiplication-by-scalar
func ec_mulmuladd{range_check_ptr}(G: EcPoint, Q: EcPoint, scalar_u: felt, scalar_v: felt) -> (res: EcPoint){

    alloc_locals;
    local m;
    //Precompute H=P+Q
    let H:EcPoint=ec_add{range_check_ptr=range_check_ptr}(G,Q);
    //recover MSB bit index
    %{ ids.m=max(ids.scalar_u.bit_length(), ids.scalar_v.bit_length())-1 %}    
    //%{ print("\n length=", ids.m) %}

    //initialize R with infinity point
    let R = EcPoint(BigInt3(0, 0, 0), BigInt3(0, 0, 0));
    let (resu:EcPoint)=ec_mulmuladd_inner(R,G,Q,H, scalar_u, scalar_v, m);
   
     return (res=resu);
	
}



//non optimized version of uG+vQ
func ec_mulmuladd_naive{range_check_ptr}(G: EcPoint, Q: EcPoint, scalar_u: BigInt3, scalar_v: BigInt3) -> (res: EcPoint){
  alloc_locals;
 
  let uG:EcPoint=ec_mul(G,scalar_u);
  let vQ:EcPoint=ec_mul(Q,scalar_v);
  let res:EcPoint=ec_add(uG,vQ);
  return (res=res);

}





